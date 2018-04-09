from abc import ABC

from nkms_eth.config import EthereumConfig


class TheBlockchain(ABC):
    """
    http://populus.readthedocs.io/en/latest/config.html#chains

    mainnet: Connects to the public ethereum mainnet via geth.
    ropsten: Connects to the public ethereum ropsten testnet via geth.
    tester: Uses an ephemeral in-memory chain backed by pyethereum.
    testrpc: Uses an ephemeral in-memory chain backed by pyethereum.
    temp: Local private chain whos data directory is removed when the chain is shutdown. Runs via geth.
    """

    _network = NotImplemented
    _default_timeout = NotImplemented
    __instance = None

    test_chains = ('tester', )
    transient_chains = test_chains + ('testrpc', 'temp')
    public_chains = ('mainnet', 'ropsten')

    class IsAlreadyRunning(RuntimeError):
        pass

    def __init__(self, eth_config: EthereumConfig):
        """
        Configures a populus project and connects to blockchain.network.
        Transaction timeouts specified measured in seconds.

        http://populus.readthedocs.io/en/latest/chain.wait.html

        """

        # Singleton
        if TheBlockchain.__instance is not None:
            message = '{} is already running on {}. Use .get() to retrieve'.format(self.__class__.__name__, self._network)
            raise TheBlockchain.IsAlreadyRunning(message)
        TheBlockchain.__instance = self

        self._eth_config = eth_config
        self._chain = eth_config.provider  # TODO

    @classmethod
    def get(cls):
        if cls.__instance is None:
            class_name = cls.__name__
            raise Exception('{} has not been created.'.format(class_name))
        return cls.__instance

    def disconnect(self):
        self._chain.__exit__(None, None, None)

    def __del__(self):
        self.disconnect()

    def __repr__(self):
        class_name = self.__class__.__name__
        r = "{}(network={})"
        return r.format(class_name, self._network)

    def get_contract(self, name):
        """
        Gets an existing contract from the network,
        or raises populus.contracts.exceptions.UnknownContract
        if there is no contract data available for the name/identifier.
        """
        return self._chain.provider.get_contract(name)

    def wait_for_receipt(self, txhash, timeout=None) -> None:
        if timeout is None:
            timeout = self._default_timeout

        result = self._chain.wait.for_receipt(txhash, timeout=timeout)
        return result

# class TestRpcBlockchain:
#
#     _network = 'testrpc'
#     _default_timeout = 60

