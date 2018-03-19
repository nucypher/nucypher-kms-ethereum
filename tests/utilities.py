import random

from nkms_eth.actors import Miner
from nkms_eth.agents import MinerAgent
from nkms_eth.blockchain import TheBlockchain
from nkms_eth.config import NuCypherMinerConfig
from nkms_eth.deployers import MinerEscrowDeployer, NuCypherKMSTokenDeployer


class TesterBlockchain(TheBlockchain):
    """Transient chain"""
    _network = 'tester'


class MockNuCypherKMSTokenDeployer(NuCypherKMSTokenDeployer):

    def _global_airdrop(self, amount: int):
        """Airdrops from creator address to all other addresses!"""

        _creator, *addresses = self._blockchain._chain.web3.eth.accounts

        def txs():
            for address in addresses:
                yield self._contract.transact({'from': self.origin}).transfer(address, amount * (10 ** 6))

        for tx in txs():
            self._blockchain._chain.wait.for_receipt(tx, timeout=10)

        return self


class MockNuCypherMinerConfig(NuCypherMinerConfig):
    """Speed things up a bit"""
    _hours_per_period = 1  # Hours
    _min_release_periods = 1


class MockMinerEscrowDeployer(MinerEscrowDeployer, MockNuCypherMinerConfig):
    pass


def spawn_miners(addresses, miner_agent, locktime=1, m=None) -> None:
    """
    Deposit and lock a random amount of tokens in the miner escrow
    from each address, "spawning" new Miners.
    """
    if m is None:
        m = 10 ** 6

    # Create n Miners
    for address in addresses:
        miner = Miner(miner_agent=miner_agent, address=address)
        amount = (10+random.randrange(9000)) * m
        miner.lock(amount=amount, locktime=locktime)
