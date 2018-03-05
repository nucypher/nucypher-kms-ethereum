from typing import Tuple

from .escrow import Escrow


class Miner:
    """
    Practically carrying a pickaxe.
    Intended for use as an Ursula mixin.

    Accepts a running blockchain, deployed token contract, and deployed escrow contract.
    If the provided token and escrow contracts are not deployed,
    ContractDeploymentError will be raised.

    """

    def __init__(self, escrow: Escrow, address=None):

        self.escrow = escrow
        if not escrow._contract:
            raise Escrow.ContractDeploymentError('Escrow contract not deployed. Arm then deploy.')
        else:
            escrow.miners.append(self)

        self._token = escrow.token
        self._blockchain = self._token.blockchain

        self.address = address

    def __repr__(self):
        class_name = self.__class__.__name__
        r = "{}(address='{}')"
        r.format(class_name, self.address)
        return r

    def __del__(self):
        """Removes this miner from the escrow's list of miners on delete."""
        self.escrow.miners.remove(self)

    def _approve_escrow(self, amount: int) -> str:
        """Approve the transfer of token from the miner's address to the escrow contract."""

        txhash = self.token.transact({'from': self.address}).approve(self.escrow.contract.address, amount)
        self.blockchain._chain.wait.for_receipt(txhash, timeout=self.blockchain._timeout)

        return txhash

    def _send_tokens_to_escrow(self, amount, locktime) -> str:
        """Send tokes to the escrow from the miner's address"""

        deposit_txhash = self.escrow.transact({'from': self.address}).deposit(amount, locktime)
        self.blockchain._chain.wait.for_receipt(deposit_txhash, timeout=self.blockchain._timeout)

        return deposit_txhash

    def lock(self, amount: int, locktime: int) -> Tuple[str, str, str]:
        """Deposit and lock tokens for mining."""

        approve_txhash = self._approve_escrow(amount=amount)
        deposit_txhash = self._send_tokens_to_escrow(amount=amount, locktime=locktime)

        lock_txhash = self.escrow.transact({'from': self.address}).switchLock()
        self.blockchain._chain.wait.for_receipt(lock_txhash, timeout=self.blockchain._timeout)

        return approve_txhash, deposit_txhash, lock_txhash

    def mint(self) -> str:
        """Computes and transfers tokens to the miner's account"""

        txhash = self.escrow.transact({'from': self.address}).mint()
        self.blockchain._chain.wait.for_receipt(txhash, timeout=self.blockchain._timeout)

        return txhash

    def collect_reward(self):
        """Collect policy reward"""

        txhash = self.policy_manager.transact({'from': self.address}).withdraw()
        self.blockchain._chain.wait.for_receipt(txhash)

        return txhash

    def publish_miner_id(self, miner_id) -> str:
        """Store a new Miner ID"""

        txhash = self.escrow.transact({'from': self.address}).setMinerId(miner_id)
        self.blockchain._chain.wait.for_receipt(txhash)

        return txhash

    def fetch_miner_ids(self) -> tuple:
        """Retrieve all stored Miner IDs on this miner"""

        count = self.escrow().getMinerIdsCount(self.address)

        miner_ids = []
        for index in range(count):
            miner_id = self.escrow().getMinerId(self.address, index)
            encoded_miner_id = miner_id.encode('latin-1')  # TODO change when v4 of web3.py is released
            miner_ids.append(encoded_miner_id)

        return tuple(miner_ids)

    def confirm_activity(self) -> str:
        """Miner rewarded for every confirmed period"""

        txhash = self.escrow.contract.transact({'from': self.address}).confirmActivity()
        self.blockchain._chain.wait.for_receipt(txhash)

        return txhash

    def balance(self) -> int:
        """Check miner's current balance"""

        self.token._check_contract_deployment()
        balance = self.token().balanceOf(self.address)

        return balance
