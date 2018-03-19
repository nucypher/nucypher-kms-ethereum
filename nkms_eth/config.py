from abc import ABC
from os.path import dirname, join, abspath

import appdirs
import populus

import nkms_eth


class NuCypherTokenConfig:
    __subdigits = 18
    _M = 10 ** __subdigits
    __premine = int(1e9) * _M
    __saturation = int(1e10) * _M
    _reward = __saturation - __premine

    @property
    def saturation(self):
        return self.__saturation


class NuCypherMinerConfig:
    _hours_per_period = 24       # Hours
    _min_release_periods = 30    # 720 Hours
    __max_awarded_periods = 365

    __min_allowed_locked = 10 ** 6
    __max_allowed_locked = 10 ** 7 * NuCypherTokenConfig._M

    __reward = NuCypherTokenConfig._reward

    __mining_coeff = [
        _hours_per_period,
        2 * 10 ** 7,
        __max_awarded_periods,
        __max_awarded_periods,
        _min_release_periods,
        __min_allowed_locked,
        __max_allowed_locked
    ]

    null_address = '0x' + '0' * 40

    @property
    def mining_coefficient(self):
        return self.__mining_coeff

    @property
    def reward(self):
        return self.__reward


class PopulusConfig:

    def __init__(self, project_name='nucypher-kms', registrar_path=None):
        self._python_project_name = project_name

        # This config is persistent and is created in user's .local directory
        if registrar_path is None:
            registrar_path = join(appdirs.user_data_dir(self._python_project_name), 'registrar.json')
        self._registrar_path = registrar_path

        # Populus project config
        self._project_dir = join(dirname(abspath(nkms_eth.__file__)), 'project')
        self._populus_project = populus.Project(self._project_dir)
        self.project.config['chains.mainnetrpc.contracts.backends.JSONFile.settings.file_path'] = self._registrar_path

    @property
    def project(self):
        return self._populus_project
