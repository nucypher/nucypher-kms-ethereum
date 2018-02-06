import random
from typing import List

from .blockchain import Blockchain
from .token import NuCypherKMSToken

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

        with blockchain as chain:
            creator = chain.web3.eth.accounts[0]  # TODO: make it possible to override
            if not contract:
                contract, txhash = chain.provider.deploy_contract(
                    self.escrow_name,
                    deploy_args=[token.contract.address]+self.mining_coeff,
                    deploy_transaction={'from': creator})

                chain.wait.for_receipt(txhash, timeout=blockchain.timeout)
                txhash = token.contract.transact({'from': creator}).addMiner(contract.address)
                chain.wait.for_receipt(txhash, timeout=blockchain.timeout)

            self.contract = contract

    def __call__(self, *args, **kwargs):
        return self.contract.call()

    @classmethod
    def get(cls, blockchain, token):
        """ Returns an escrow object or an error """
        contract = blockchain.get_contract(cls.escrow_name)
        return cls(blockchain=blockchain, token=token, contract=contract)

    def confirm_activity(self, address):
        """Confirm activity for future period"""
        return self.contract.transact({'from': address}).confirmActivity()

    def sample(self, quantity: int=10, additional_ursulas: float=1.7, attempts: int=5) -> List[addr]:
        """
        Select n random staking Ursulas, according to their stake distribution.
        The returned addresses are shuffled, so one can request more than needed and
        throw away those which do not respond.
        """

        n_select = round(quantity*additional_ursulas)            # Select more Ursulas
        n_tokens = self().getAllLockedTokens()
        duration = 10

        for _ in range(attempts):  # number of tries
            points = [0] + sorted(random.randrange(n_tokens) for _ in range(n_select))
            deltas = [i-j for i, j in zip(points[1:], points[:-1])]

            addrs, addr, shift = set(), self.null_addr, 0
            for delta in deltas:
                addr, shift = self().findCumSum(addr, delta+shift, duration)
                addrs.add(addr)

            if len(addrs) >= quantity:
                return random.sample(addrs, quantity)

        raise Blockchain.NotEnoughUrsulas('Not enough Ursulas.')
