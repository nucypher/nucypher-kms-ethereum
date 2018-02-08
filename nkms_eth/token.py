from populus.contracts.contract import PopulusContract
from .blockchain import Blockchain


class NuCypherKMSToken:
    token_name = 'NuCypherKMSToken'
    subdigits = 18
    M = 10 ** subdigits
    premine = int(1e9) * M
    saturation = int(1e10) * M

    def __init__(self, blockchain: Blockchain, token_contract: PopulusContract = None):
            self.creator = blockchain.web3.eth.accounts[0]

            if not token_contract:
                token_contract, txhash = blockchain.chain.provider.get_or_deploy_contract(
                                   self.token_name,
                                   deploy_args=[self.premine, self.saturation],
                                   deploy_transaction={'from': self.creator})
                if not txhash:
                    raise Exception('Token already deployed. use .get() instead.')

                blockchain.chain.wait.for_receipt(txhash, timeout=blockchain.timeout)

            self.blockchain = blockchain
            self.contract = token_contract

    def __repr__(self):
        class_name = self.__class__.__name__
        return "{}(blockchain={})".format(class_name, self.blockchain)

    def __eq__(self, other):
        return self.contract.address == other.contract.address

    def __call__(self, *args, **kwargs):
        """Invoke contract -> No state change"""
        return self.contract.call(*args, **kwargs)

    def transact(self, wait=True, *args, **kwargs):
        """Invoke contract -> State change"""
        tx_hash = self.contract.transact(*args, **kwargs)
        if wait:
            self.blockchain.chain.wait.for_receipt(tx_hash)
        return tx_hash

    @classmethod
    def get(cls, blockchain):
        """Gets an existing token contract or returns an error"""
        contract = blockchain.chain.provider.get_contract(cls.token_name)
        return cls(blockchain=blockchain, token_contract=contract)

    def get_addresses(self):
        """Retrieve all known addresses for this contract"""
        return self.blockchain.chain.registrar.get_contract_address(self.token_name)

    def balance(self, address: str):
        """Get the balance of a token address"""
        return self().balanceOf(address)

    def _airdrop(self, amount: int=10000) -> None:
        """ Airdrops from creator address to others """
        creator, *addresses = self.blockchain.web3.eth.accounts

        def txs():
            for address in addresses:
                yield self.transact({'from': self.creator}).transfer(address, amount*(10**6))

        for tx in txs():
            self.blockchain.chain.wait.for_receipt(tx, timeout=10)

        return
