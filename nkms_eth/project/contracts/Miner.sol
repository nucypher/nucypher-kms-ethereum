pragma solidity ^0.4.0;


import "./NuCypherKMSToken.sol";
import "./zeppelin/math/SafeMath.sol";


/**
* @notice Contract for minting tokens
**/
contract Miner {
    using SafeMath for uint256;

    NuCypherKMSToken token;
    uint256 public miningCoefficient;
    uint256 public secondsPerPeriod;
    uint256 public lockedPeriodsCoefficient;
    uint256 public awardedPeriods;

    uint256 public lastMintedPeriod;
    mapping (byte => uint256) public totalSupply;
    byte public currentIndex;
    uint256 futureSupply;

    byte NEGATION = 0xF0;

    /**
    * @notice The Miner constructor sets address of token contract and coefficients for mining
    * @dev Formula for mining in one period
    (futureSupply - currentSupply) * (lockedValue / totalLockedValue) * (k1 + allLockedPeriods) / k2
    if allLockedPeriods > awardedPeriods then allLockedPeriods = awardedPeriods
    * @param _token Token contract
    * @param _hoursPerPeriod Size of period in hours
    * @param _miningCoefficient Mining coefficient (k2)
    * @param _lockedPeriodsCoefficient Locked blocks coefficient (k1)
    * @param _awardedPeriods Max periods that will be additionally awarded
    **/
    function Miner(
        NuCypherKMSToken _token,
        uint256 _hoursPerPeriod,
        uint256 _miningCoefficient,
        uint256 _lockedPeriodsCoefficient,
        uint256 _awardedPeriods
    ) {
        require(address(_token) != 0x0 &&
            _miningCoefficient != 0 &&
            _hoursPerPeriod != 0 &&
            _lockedPeriodsCoefficient != 0 &&
            _awardedPeriods != 0);
        token = _token;
        miningCoefficient = _miningCoefficient;
        secondsPerPeriod = _hoursPerPeriod.mul(1 hours);
        lockedPeriodsCoefficient = _lockedPeriodsCoefficient;
        awardedPeriods = _awardedPeriods;

        lastMintedPeriod = getCurrentPeriod();
        currentIndex = 0x01;
        var currentTotalSupply = token.totalSupply();
        totalSupply[currentIndex] = currentTotalSupply;
        totalSupply[currentIndex ^ NEGATION] = currentTotalSupply;
        futureSupply = token.futureSupply();
    }

    /**
    * @return Number of current period
    **/
    function getCurrentPeriod() public constant returns (uint256) {
        return block.timestamp / secondsPerPeriod;
    }

    /**
    * @notice Function to mint tokens for sender for one period.
    * @param _to The address that will receive the minted tokens.
    * @param _period Period number.
    * @param _lockedValue The amount of tokens that were locked by user in specified period.
    * @param _totalLockedValue The amount of tokens that were locked by all users in specified period.
    * @param _allLockedPeriods The max amount of periods during which tokens will be locked after specified period.
    * @param _decimals The amount of locked tokens and blocks in decimals.
    * @return Amount of minted tokens.
    */
    // TODO decimals
    function mint(
        address _to,
        uint256 _period,
        uint256 _lockedValue,
        uint256 _totalLockedValue,
        uint256 _allLockedPeriods,
        uint256 _decimals
    )
        internal returns (uint256 amount, uint256 decimals)
    {
        // TODO end of mining before calculation
        var nextTotalSupply = totalSupply[currentIndex ^ NEGATION];
        if (_period > lastMintedPeriod) {
            currentIndex = currentIndex ^ NEGATION;
            lastMintedPeriod = _period;
        }

        //futureSupply * lockedValue * (k1 + allLockedPeriods) / (totalLockedValue * k2) -
        //currentSupply * lockedValue * (k1 + allLockedPeriods) / (totalLockedValue * k2)
        var allLockedPeriods = (_allLockedPeriods <= awardedPeriods ?
            _allLockedPeriods : awardedPeriods)
            .add(lockedPeriodsCoefficient);
        var denominator = _totalLockedValue.mul(miningCoefficient);
        amount =
            futureSupply
                .mul(_lockedValue)
                .mul(allLockedPeriods)
                .div(denominator).sub(
            totalSupply[currentIndex]
                .mul(_lockedValue)
                .mul(allLockedPeriods)
                .div(denominator));
        token.mint(_to, amount);

        totalSupply[currentIndex ^ NEGATION] = nextTotalSupply.add(amount);
    }
}
