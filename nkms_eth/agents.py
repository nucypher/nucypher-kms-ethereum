import random
from typing import Set, Generator

from nkms_eth.actors import PolicyAuthor
from nkms_eth.base import ContractAgent
from nkms_eth.deployers import MinerEscrowDeployer, NuCypherKMSTokenDeployer, PolicyManagerDeployer


class NuCypherKMSTokenAgent(ContractAgent):

    __deployer = NuCypherKMSTokenDeployer
    _contract_name = __deployer.contract_name

    def registrar(self):
        """Retrieve all known addresses for this contract"""
        all_known_address = self._blockchain._chain.registrar.get_contract_address(self._contract_name)
        return all_known_address

    def check_balance(self, address: str) -> int:
        """Get the balance of a token address"""
        return self.call().balanceOf(address)


class MinerAgent(ContractAgent):
    """
    Wraps NuCypher's Escrow solidity smart contract, and manages a PopulusContract.

    In order to become a participant of the network,
    a miner locks tokens by depositing to the Escrow contract address
    for a duration measured in periods.

    """
    __deployer = MinerEscrowDeployer
    _contract_name = __deployer.contract_name

    class NotEnoughUrsulas(Exception):
        pass

    def __init__(self, token: NuCypherKMSTokenAgent):
        super().__init__(agent=token)
        self._token = token
        self.miners = list()

    def get_miner_ids(self) -> Set[str]:
        """
        Fetch all miner IDs from the local cache and return them in a set
        """
        return {miner.get_id() for miner in self.miners}

    def swarm(self) -> Generator[str, None, None]:
        """
        Generates all miner addresses via cumulative sum on-network.
        """
        miner, i = MinerEscrowDeployer.null_address, 0
        while True:

            # Get the next miner
            next_miner = self.call().getNextMiner(miner)

            if next_miner == MinerEscrowDeployer.null_address:
                raise StopIteration()

            yield next_miner

            # Advance
            miner = next_miner
            i += 1

    def sample(self, quantity: int=10, additional_ursulas: float=1.7, attempts: int=5, duration: int=10) -> List[addr]:
        """
        Select n random staking Ursulas, according to their stake distribution.
        The returned addresses are shuffled, so one can request more than needed and
        throw away those which do not respond.

                  _start
                  v
        |-------->*--------------->*---->*------------->|
                  |                      ^
                  |                      stop
                  |
                  |       _delta
                  |---------------------------->|
                  |
                  |                       shift
                  |                      |----->|

        See full diagram here: https://github.com/nucypher/kms-whitepaper/blob/master/pdf/miners-ruler.pdf

        """

        system_random = random.SystemRandom()
        n_select = round(quantity*additional_ursulas)            # Select more Ursulas
        n_tokens = self.call().getAllLockedTokens()

        if not n_tokens > 0:
            raise self.NotEnoughUrsulas('There are no locked tokens.')

        for _ in range(attempts):
            points = [0] + sorted(system_random.randrange(n_tokens) for _ in range(n_select))
            deltas = [i-j for i, j in zip(points[1:], points[:-1])]

            addrs, addr, shift = set(), MinerEscrowDeployer.null_address, 0
            for delta in deltas:
                addr, shift = self.call().findCumSum(addr, delta+shift, duration)
                addrs.add(addr)

            if len(addrs) >= quantity:
                return system_random.sample(addrs, quantity)

        raise self.NotEnoughUrsulas('Selection failed after {} attempts'.format(attempts))


class PolicyAgent(ContractAgent):

    __deployer = PolicyManagerDeployer
    _contract_name = __deployer.contract_name

    def fetch_arrangement_data(self, arrangement_id: bytes) -> list:
        blockchain_record = self.call().policies(arrangement_id)
        return blockchain_record

    def revoke_arrangement(self, arrangement_id: bytes, author: 'PolicyAuthor', gas_price: int):
        """
        Revoke by arrangement ID; Only the policy author can revoke the policy
        """
        txhash = self.transact({'from': author.address, 'gas_price': gas_price}).revokePolicy(arrangement_id)
        self._blockchain._chain.wait.for_receipt(txhash)
        return txhash
