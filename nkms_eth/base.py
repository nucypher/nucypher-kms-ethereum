from abc import ABC, abstractmethod

from nkms_eth.blockchain import TheBlockchain


class Actor(ABC):
    def __init__(self, address):
        if isinstance(address, bytes):
            address = address.hex()
        self.address = address

    def __repr__(self):
        class_name = self.__class__.__name__
        r = "{}(address='{}')"
        r.format(class_name, self.address)
        return r

class ContractController(ABC):
    """Abstract base class for contract deployers and agents"""
    def __init__(self, blockchain: TheBlockchain):
        self._blockchain = blockchain


class ContractDeployer(ABC, ContractController):
    __contract_name = None

    class ContractDeploymentError(Exception):
        pass

    def __init__(self, *args, **kwargs):
        self._armed = False
        self.__contract = None
        super().__init__(*args, **kwargs)

    def __eq__(self, other):
        return self.__contract.address == other.address

    @property
    def address(self):
        return self.__contract.address

    @property
    def is_deployed(self):
        return bool(self._contract is not None)

    @property
    @classmethod
    def contract_name(cls):
        return cls.__contract_name

    def arm(self) -> None:
        self._armed = True
        return None

    @abstractmethod
    def deploy(self):
        raise NotImplementedError

    def _check_contract_deployment(self) -> None:
        """Raises ContractDeploymentError if the contract has not been armed and deployed."""
        if not self._contract:
            class_name = self.__class__.__name__
            message = '{} contract is not deployed. Arm, then deploy.'.format(class_name)
            raise self.ContractDeploymentError(message)

    # @classmethod
    # def from_blockchain(cls, blockchain: TheBlockchain):
    #     """
    #     Returns the NuCypherKMSToken object,
    #     or raises UnknownContract if the contract has not been deployed.
    #     """
    #     contract = blockchain._chain.provider.get_contract(cls.contract_name)
    #     instance = cls(blockchain=blockchain)
    #     instance._contract = contract
    #     return instance


class ContractAgent(ABC, ContractController):
    _contract_name = None

    class ContractNotDeployed(Exception):
        pass

    def __init__(self, agent, *args, **kwargs):
        contract = agent._blockchain._chain.provider.get_contract(agent._contract_name)
        self._contract = contract
        super().__init__(blockchain=agent._blockchain)

    def call(self):
        return self._contract.call()

    def transact(self, *args, **kwargs):
        return self._contract.transact(*args, **kwargs)
