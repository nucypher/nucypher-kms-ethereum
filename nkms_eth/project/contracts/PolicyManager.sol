pragma solidity ^0.4.0;


import "./zeppelin/token/SafeERC20.sol";
import "./zeppelin/math/SafeMath.sol";
import "./zeppelin/math/Math.sol";
import "./Escrow.sol";
import "./NuCypherKMSToken.sol";


/**
* @notice Contract holds policy data and locks fees
**/
contract PolicyManager {
    using SafeERC20 for NuCypherKMSToken;
    using SafeMath for uint256;

//    enum PolicyState { Pending, Active }
//    enum PolicyType { Periods }

    struct Policy {
        address client;
        address node;
//        PolicyState state;

        // policy for activity periods
        uint256 rate;
        uint256 startPeriod;
        uint256 lastPeriod;
        uint256 indexOfDowntimePeriods;
    }

    struct NodeInfo {
        mapping (uint256 => uint256) rewardByPeriod;
        uint256 reward;
    }

    NuCypherKMSToken public token;
    Escrow public escrow;
    mapping (bytes20 => Policy) public policies;
    mapping (address => NodeInfo) public nodes;
//    mapping (address => byte20[]) nodePolicies;
//    mapping (address => byte20[]) clientPolicies;

    /**
    * @notice The PolicyManager constructor sets addresses of token and escrow contracts
    * @param _token Token contract
    * @param _escrow Escrow contract
    **/
    function PolicyManager(
        NuCypherKMSToken _token,
        Escrow _escrow
    ) {
        require(address(_token) != 0x0);
        token = _token;
        escrow = _escrow;
    }

    /**
    * @notice Create policy by client
    * @dev Generate policy id before creation
    * @param _policyId Policy id
    * @param _feeByPeriod Amount of node reward by period
    * @param _node Node that will handle policy
    * @param _numberOfPeriods Duration of the policy in periods
    **/
    function createPolicy(
        bytes20 _policyId,
        uint256 _feeByPeriod,
        address _node,
        uint256 _numberOfPeriods
    )
        public
    {
        require(
            policies[_policyId].rate == 0 &&
            _feeByPeriod != 0 &&
            _numberOfPeriods != 0 &&
            escrow.getLockedTokens(_node) != 0
        );
        token.safeTransferFrom(
            msg.sender, address(this), _feeByPeriod.mul(_numberOfPeriods));
        var policy = policies[_policyId];
        policy.client = msg.sender;
        policy.node = _node;
//        policy.state = PolicyState.Pending;
        var currentPeriod = escrow.getCurrentPeriod();
        policy.startPeriod = currentPeriod.add(1);
        policy.lastPeriod = currentPeriod.add(_numberOfPeriods);
        policy.rate = _feeByPeriod;

        var node = nodes[_node];
        for (uint256 i = policy.startPeriod; i <= policy.lastPeriod; i++) {
            node.rewardByPeriod[i] = node.rewardByPeriod[i].add(_feeByPeriod);
        }
        policy.indexOfDowntimePeriods = escrow.getDowntimePeriodsLength(_node);
    }

//    /**
//    * @notice Confirm policy by node
//    * @param _policyId Policy id
//    **/
//    function confirmPolicy(bytes20 _policyId) public {
//        var policy = policies[_policyId];
//        require(policy.state == PolicyState.Pending &&
//            policy.node == msg.sender);
//        policy.state = PolicyState.Active;
//    }

    /**
    * @notice Update node reward
    * @param _node Node address
    * @param _period Processed period
    **/
    function updateReward(address _node, uint256 _period) external {
        require(msg.sender == address(escrow));
        var node = nodes[_node];
        node.reward = node.reward.add(node.rewardByPeriod[_period]);
        delete node.rewardByPeriod[_period];
    }

    /**
    * @notice Withdraw fee by node
    **/
    function withdraw() public {
        var node = nodes[msg.sender];
        var reward = node.reward;
        require(reward != 0);
        node.reward = 0;
        token.safeTransfer(msg.sender, reward);
    }

    /**
    * @notice Revoke policy by client
    * @param _policyId Policy id
    **/
    function revokePolicy(bytes20 _policyId) public {
        var policy = policies[_policyId];
        require(policy.client == msg.sender);
        var refund = calculateRefund(policy);
        var node = nodes[policy.node];
        for (var i = policy.startPeriod; i <= policy.lastPeriod; i++) {
            node.rewardByPeriod[i] = node.rewardByPeriod[i].sub(policy.rate);
            refund = refund.add(policy.rate);
        }
        delete policies[_policyId];
        token.safeTransfer(msg.sender, refund);
    }

    /**
    * @notice Refund part of fee by client
    * @param _policyId Policy id
    **/
    function refund(bytes20 _policyId) public {
        var policy = policies[_policyId];
//        require(policy.state == PolicyState.Active &&
//            msg.sender == policy.client);
        require(msg.sender == policy.client);

        var refund = calculateRefund(policy);
        if (policy.startPeriod > policy.lastPeriod) {
            delete policies[_policyId];
        }
        if (refund > 0) {
            token.safeTransfer(policy.client, refund);
        }
    }

    /**
    * @notice Calculate amount of refund
    * @param policy Policy
    **/
    function calculateRefund(Policy policy) internal returns (uint256) {
        var currentPeriod = escrow.getCurrentPeriod();
        var maxPeriod = Math.min256(currentPeriod, policy.lastPeriod);
        var minPeriod = policy.startPeriod;
        var max = maxPeriod;
        var activePeriods = maxPeriod.add(1).sub(minPeriod);
        var length = escrow.getDowntimePeriodsLength(policy.node);
        // TODO complete
        for (var i = policy.indexOfDowntimePeriods; i < length; i++) {
            var (startPeriod, endPeriod) = escrow.getDowntimePeriods(policy.node, i);
            if (startPeriod > maxPeriod) {
                break;
            } else if (endPeriod < minPeriod) {
                continue;
            }
            max = Math.min256(maxPeriod, endPeriod);
            var min = Math.max256(minPeriod, startPeriod);
            // TODO safe math
            activePeriods -= max - min + 1;
            if (maxPeriod <= endPeriod) {
                break;
            }
        }
        policy.indexOfDowntimePeriods = i;
        var lastActivePeriod = escrow.getLastActivePeriod(policy.node);
        if (i == length && lastActivePeriod < maxPeriod) {
            min = Math.max256(minPeriod, lastActivePeriod);
            // TODO safe math
            activePeriods -= max - min + 1;
        }
        policy.startPeriod = max.add(1);

        return policy.rate.mul(activePeriods);
    }

}