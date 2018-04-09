import pytest
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from nkms_eth.agents import NuCypherKMSTokenAgent, MinerAgent, PolicyAgent
from nkms_eth.blockchain import TheBlockchain
from nkms_eth.config import EthereumConfig
from nkms_eth.deployers import PolicyManagerDeployer
from nkms_eth.utilities import TesterBlockchain, MockNuCypherKMSTokenDeployer, MockMinerEscrowDeployer, MockMinerAgent
from eth_tester import EthereumTester


@pytest.fixture(scope='session')
def testerchain():
    tester = EthereumTester()
    test_provider = EthereumTesterProvider(ethereum_tester=tester)
    web3_provider = Web3(providers=test_provider)
    ethconfig = EthereumConfig(provider=web3_provider)
    testerchain = TesterBlockchain(eth_config=ethconfig)
    yield testerchain

    del testerchain
    TheBlockchain._TheBlockchain__instance = None


@pytest.fixture()
def mock_token_deployer(testerchain):
    token_deployer = MockNuCypherKMSTokenDeployer(blockchain=testerchain)
    token_deployer.arm()
    token_deployer.deploy()
    yield token_deployer


@pytest.fixture()
def mock_miner_escrow_deployer(token_agent):
    escrow = MockMinerEscrowDeployer(token_agent=token_agent)
    escrow.arm()
    escrow.deploy()
    yield escrow


@pytest.fixture()
def mock_policy_manager_deployer(mock_token_deployer):
    policy_manager_deployer = PolicyManagerDeployer(token_deployer=mock_token_deployer)
    policy_manager_deployer.arm()
    policy_manager_deployer.deploy()
    yield policy_manager_deployer


#
# Unused args preserve fixture dependency order #
#

@pytest.fixture()
def token_agent(testerchain, mock_token_deployer):
    token = NuCypherKMSTokenAgent(blockchain=testerchain)
    yield token


@pytest.fixture()
def mock_miner_agent(token_agent, mock_token_deployer, mock_miner_escrow_deployer):
    miner_agent = MinerAgent(token_agent=token_agent)
    yield miner_agent


@pytest.fixture()
def mock_policy_agent(mock_miner_agent, token_agent, mock_token_deployer, mock_miner_escrow_deployer):
    policy_agent = PolicyAgent(miner_agent=mock_miner_agent)
    yield policy_agent
