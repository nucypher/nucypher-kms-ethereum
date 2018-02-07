import random
import pytest

from nkms_eth.escrow import Escrow
from nkms_eth.miner import Miner
from nkms_eth.token import NuCypherKMSToken

M = 10 ** 6


def test_deposit(testerchain, miner, token):
    token.airdrop()
    miner.lock(amount=1000*M, locktime=100, address=testerchain.web3.eth.accounts[1])


def test_select_ursulas(testerchain, token, escrow, miner):

    token.airdrop()
    # Create a random set of miners (we have 9 in total)
    for u in testerchain.web3.eth.accounts[1:]:
        miner.lock((10 + random.randrange(9000))*M, 100, u)
        testerchain.chain.wait.for_block(testerchain.web3.eth.blockNumber+escrow.hours_per_period)

    miners = escrow.sample(quantity=3)
    assert len(miners) == 3
    assert len(set(miners)) == 3

    with pytest.raises(Exception):
        escrow.sample(quantity=100)  # Waay more than we have deployed


def test_mine_withdraw(testerchain, miner, token, escrow):
    token.airdrop()

    addr = testerchain.web3.eth.accounts[1]
    initial_balance = token.balance(addr)

    # Create a random set of miners (we have 9 in total)
    for u in testerchain.web3.eth.accounts[1:]:
        miner.lock(amount=(10 + random.randrange(9000))*M, locktime=1, address=u)
        testerchain.chain.wait.for_block(testerchain.web3.eth.blockNumber + 2 * escrow.hours_per_period)

    miner.mine(addr)
    miner.withdraw(addr)
    final_balance = token.balance(addr)

    assert final_balance > initial_balance
