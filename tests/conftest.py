import pytest

from nkms_eth.blockchain import Blockchain
from nkms_eth.token import NuCypherKMSToken
from tests.utilities import TesterBlockchain, MockMinerEscrow


@pytest.fixture(scope='function')
def testerchain():
    chain = TesterBlockchain()
    yield chain
    del chain
    TesterBlockchain._instance = None


@pytest.fixture(scope='function')
def token(testerchain):
    token = NuCypherKMSToken(blockchain=testerchain)
    token.arm()
    token.deploy()
    yield token


@pytest.fixture(scope='function')
def escrow(token):
    escrow = MockMinerEscrow(token=token)
    escrow.arm()
    escrow.deploy()
    yield escrow