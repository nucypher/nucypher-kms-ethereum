

class NuCypherKMSToken(object):
    contract_name = 'NuCypherKMSToken'  # TODO this should be NuCypher's class
    subdigits = 18
    M = 10 ** subdigits
    premine = int(1e9) * M
    saturation = int(1e10) * M

    def __init__(self, blockchain, contract=None):
        self.blockchain = blockchain

        with self.blockchain as chain:
            creator = chain.web3.eth.accounts[0]              # TODO: make it possible to override
            if not contract:
                contract, txhash = chain.provider.deploy_contract(
                                   self.contract_name,
                                   deploy_args=[self.premine, self.saturation],
                                   deploy_transaction={'from': creator})

                chain.wait.for_receipt(txhash, timeout=self.blockchain.timeout)

            self.contract = contract

    def __repr__(self):
        class_name = self.__class__.__name__
        return f"{class_name}(blockchain={self.blockchain})"

    def __call__(self, *args, **kwargs):
        return self.contract.call(*args, **kwargs)

    def balance(self, address: str):
        return self().balanceOf(address)

    @classmethod
    def get(cls, blockchain):
        """Gets an existing contract or returns an error"""
        contract = blockchain.get_contract(cls.contract_name)
        return cls(blockchain=blockchain, contract=contract)
