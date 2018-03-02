from typing import Tuple

from nkms_eth.blockchain import Blockchain
from nkms_eth.escrow import Escrow
from nkms_eth.token import NuCypherKMSToken

from collections import namedtuple


Policy = namedtuple('Policy', 'policy_id client miner_addr rate duration')

class Policy:
    def __init__(self, policy_id, client_addr, miner_addr, rate, duration):
        self._policy_id = policy_id
        self.client_address = client_addr
        self.node_address = miner_addr
        self.rate = rate
        self.duration = duration


class PolicyManager:

    __contract_name = 'PolicyManager'

    class ContractDeploymentError(Exception):
        pass

    def __init__(self, blockchain: Blockchain, token: NuCypherKMSToken, escrow: Escrow):
        self.blockchain = blockchain
        self.token = token
        self.escrow = escrow    # TODO: must be deployed
        self.armed = False
        self.__contract = None

    def arm(self) -> None:
        self.armed = True

    def deploy(self) -> Tuple[str, str]:
        if not self.armed:
            raise PolicyManager.ContractDeploymentError('Contract not armed')
        if self.__contract is not None:
            raise PolicyManager.ContractDeploymentError

        # Creator deploys the policy manager
        the_policy_manager_contract, deploy_txhash = self.blockchain._chain.provider.deploy_contract(
            self.__contract_name,
            deploy_args=[self.token.contract.address, self.escrow.contract.address],
            deploy_transaction={'from': self.token.creator})

        self.__contract = the_policy_manager_contract

        set_txhash = self.escrow.transact({'from': self.token.creator}).setPolicyManager(the_policy_manager_contract.address)
        self.blockchain._chain.wait.for_receipt(set_txhash)

        return deploy_txhash, set_txhash

    @classmethod
    def get(cls, blockchain: Blockchain, token: NuCypherKMSToken) -> 'PolicyManager':
        contract = blockchain._chain.provider.get_contract(cls.__contract_name)
        instance = cls(blockchain=blockchain, token=token)
        instance.__contract = contract
        return instance

    def transact(self, *args):
        """Transmit a network transaction."""
        return self.__contract.transact(*args)

    def create_policy(self, policy_id: bytes, client_addr: str,
                      node_addr: str, rate: int, duration: int) -> Policy:

        txhash = self.transact({'from': client_addr}).createPolicy(policy_id,
                                                                   client_addr,
                                                                   node_addr,
                                                                   rate,
                                                                   duration)
        self.blockchain._chain.wait.for_receipt(txhash)

        policy = Policy(policy_id, client_addr, node_addr, rate, duration)
        return policy

    def get_policy(self, policy_id: bytes) -> Policy:
        client_addr, node_addr, rate, *periods = self.__contract.call().policies(policy_id)
        policy = Policy(policy_id, client_addr, node_addr, rate, duration=len(periods))
        return policy


