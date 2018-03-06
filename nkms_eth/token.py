from populus.contracts.contract import PopulusContract
from .blockchain import Blockchain


class NuCypherKMSToken:
    __contract_name = 'NuCypherKMSToken'
    __subdigits = 18
    _M = 10 ** __subdigits
    __premine = int(1e9) * _M
    __saturation = int(1e10) * _M
    _reward = __saturation - __premine


    class ContractDeploymentError(Exception):
        pass

    def __init__(self, blockchain: Blockchain):
        self._creator = blockchain._chain.web3.eth.accounts[0]
        self._blockchain = blockchain
        self._contract = None
        self._armed = False

    def __repr__(self):
        class_name = self.__class__.__name__
        r = "{}(blockchain={}, contract={})"
        return r.format(class_name, self._blockchain, self._contract)

    def __eq__(self, other):
        """Two token objects are equal if they have the same contract address"""
        return self._contract.address == other._contract.address

    def __call__(self, *args, **kwargs):
        """Invoke contract -> No state change"""
        return self._contract.call(*args, **kwargs)

    def _check_contract_deployment(self) -> None:
        """Raises ContractDeploymentError if the contract has not been armed and deployed."""
        if not self._contract:
            class_name = self.__class__.__name__
            message = '{} contract is not deployed. Arm, then deploy.'.format(class_name)
            raise self.ContractDeploymentError(message)

    def arm(self) -> None:
        """Arm contract for deployment to blockchain."""
        self._armed = True

    def deploy(self) -> str:
        """
        Deploy and publish the NuCypherKMS Token contract
        to the blockchain network specified in self.blockchain.network.

        The contract must be armed before it can be deployed.
        Deployment can only ever be executed exactly once!
        """

        if self._armed is False:
            raise self.ContractDeploymentError('use .arm() to arm the contract, then .deploy().')

        if self._contract is not None:
            class_name = self.__class__.__name__
            message = '{} contract already deployed, use .get() to retrieve it.'.format(class_name)
            raise self.ContractDeploymentError(message)

        the_nucypherKMS_token_contract, deployment_txhash = self._blockchain._chain.provider.deploy_contract(
            self.__contract_name,
            deploy_args=[self.__saturation],
            deploy_transaction={'from': self._creator})

        self._blockchain._chain.wait.for_receipt(deployment_txhash, timeout=self._blockchain._timeout)

        self._contract = the_nucypherKMS_token_contract
        return deployment_txhash

    def transact(self, *args):
        """Invoke contract -> State change"""
        self._check_contract_deployment()
        result = self._contract.transact(*args)
        return result

    @classmethod
    def get(cls, blockchain):
        """
        Returns the NuCypherKMSToken object,
        or raises UnknownContract if the contract has not been deployed.
        """
        contract = blockchain._chain.provider.get_contract(cls.__contract_name)
        instance = cls(blockchain=blockchain)
        instance._contract = contract
        return instance

    def registrar(self):
        """Retrieve all known addresses for this contract"""
        self._check_contract_deployment()
        return self._blockchain._chain.registrar.get_contract_address(self.__contract_name)

    def balance(self, address: str):
        """Get the balance of a token address"""
        self._check_contract_deployment()
        return self.__call__().balanceOf(address)

    def _airdrop(self, amount: int):
        """Airdrops from creator address to all other addresses!"""
        self._check_contract_deployment()
        _, *addresses = self._blockchain._chain.web3.eth.accounts

        def txs():
            for address in addresses:
                yield self.transact({'from': self._creator}).transfer(address, amount * (10 ** 6))

        for tx in txs():
            self._blockchain._chain.wait.for_receipt(tx, timeout=10)

        return self
