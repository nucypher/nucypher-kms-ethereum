from random import SystemRandom
from typing import List

from .blockchain import Blockchain

addr = str


class Escrow:
    escrow_name = 'Escrow'
    hours_per_period = 1       # 24
    min_release_periods = 1    # 30
    max_awarded_periods = 365
    null_addr = '0x' + '0' * 40

    mining_coeff = [
        hours_per_period,
        2 * 10 ** 7,
        max_awarded_periods,
        max_awarded_periods,
        min_release_periods
    ]

    def __init__(self, blockchain, token, contract=None):

        if not contract:
            contract, txhash = blockchain.chain.provider.deploy_contract(
                self.escrow_name,
                deploy_args=[token.contract.address]+self.mining_coeff,
                deploy_transaction={'from': token.creator})

            blockchain.chain.wait.for_receipt(txhash, timeout=blockchain.timeout)
            txhash = token.contract.transact({'from': token.creator}).addMiner(contract.address)
            blockchain.chain.wait.for_receipt(txhash, timeout=blockchain.timeout)

        self.blockchain = blockchain
        self.contract = contract
        self.token = token

    def __call__(self, *args, **kwargs):
        return self.contract.call()

    def __eq__(self, other):
        return self.contract.address == other.contract.address

    @classmethod
    def get(cls, blockchain, token):
        """ Returns an escrow object or an error """
        contract = blockchain.chain.provider.get_contract(cls.escrow_name)
        return cls(blockchain=blockchain, token=token, contract=contract)

    def transact(self, *args, **kwargs):
        return self.contract.transact(*args, **kwargs)

    def confirm_activity(self, address: str) -> str:
        with self.blockchain as chain:
            tx = self.contract.transact({'from': address}).confirmActivity()
            chain.wait.for_receipt(tx)
        return tx

    def sample(self, quantity: int=10, additional_ursulas: float=1.7, attempts: int=5, duration: int=10) -> List[addr]:
        """
        Select n random staking Ursulas, according to their stake distribution.
        The returned addresses are shuffled, so one can request more than needed and
        throw away those which do not respond.
        """

        system_random = SystemRandom()
        n_select = round(quantity*additional_ursulas)            # Select more Ursulas
        n_tokens = self().getAllLockedTokens()

        if not n_tokens:
            raise Blockchain.NotEnoughUrsulas('Not enough Ursulas.')

        for _ in range(attempts):  # number of tries
            points = [0] + sorted(system_random.randrange(n_tokens) for _ in range(n_select))
            deltas = [i-j for i, j in zip(points[1:], points[:-1])]

            addrs, addr, shift = set(), self.null_addr, 0
            for delta in deltas:
                addr, shift = self().findCumSum(addr, delta+shift, duration)
                addrs.add(addr)

            if len(addrs) >= quantity:
                return system_random.sample(addrs, quantity)

        raise Blockchain.NotEnoughUrsulas('Not enough Ursulas.')
