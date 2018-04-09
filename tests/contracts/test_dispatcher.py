import pytest
from ethereum.tester import TransactionFailed
from web3.contract import Contract


def test_dispatcher(web3, chain):
    """
    These are tests for Dispatcher taken from github:
    https://github.com/willjgriff/solidity-playground/blob/master/Upgradable/ByzantiumUpgradable/test/UpgradableContractProxyTest.js
    but some of the tests are converted from javascript to python
    """

    creator = web3.eth.accounts[1]
    account = web3.eth.accounts[0]

    # Load contract interface
    contract_interface = chain.provider.get_base_contract_factory('ContractInterface')

    # Deploy contracts and dispatcher for them
    contract1_lib, _ = chain.provider.get_or_deploy_contract('ContractV1', deploy_args=[1])
    contract2_lib, _ = chain.provider.get_or_deploy_contract('ContractV2', deploy_args=[1])
    contract3_lib, _ = chain.provider.get_or_deploy_contract('ContractV3', deploy_args=[2])
    contract2_bad_lib, _ = chain.provider.get_or_deploy_contract('ContractV2Bad')
    dispatcher, _ = chain.provider.get_or_deploy_contract(
            'Dispatcher', deploy_args=[contract1_lib.address],
            deploy_transaction={'from': creator})
    assert dispatcher.call().target().lower() == contract1_lib.address

    events = dispatcher.pastEvents('Upgraded').get()
    assert 1 == len(events)
    event_args = events[0]['args']
    assert '0x' + '0' * 40 == event_args['from']
    assert contract1_lib.address.lower() == event_args['to'].lower()
    assert creator == event_args['owner']

    # Assign dispatcher address as contract.
    # In addition to the interface can be used ContractV1, ContractV2 or ContractV3 ABI
    contract_instance = web3.eth.contract(
        contract_interface.abi,
        dispatcher.address,
        ContractFactoryClass=Contract)

    # Only owner can change target address for dispatcher
    with pytest.raises(TransactionFailed):
        tx = dispatcher.transact({'from': account}).upgrade(contract2_lib.address)
        chain.wait.for_receipt(tx)
    assert dispatcher.call().target().lower() == contract1_lib.address.lower()

    # Check values before upgrade
    assert contract_instance.call().getStorageValue() == 1
    assert contract_instance.call().returnValue() == 10
    tx = contract_instance.transact().setStorageValue(5)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getStorageValue() == 5
    tx = contract_instance.transact().pushArrayValue(12)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getArrayValueLength() == 1
    assert contract_instance.call().getArrayValue(0) == 12
    tx = contract_instance.transact().pushArrayValue(232)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getArrayValueLength() == 2
    assert contract_instance.call().getArrayValue(1) == 232
    tx = contract_instance.transact().setMappingValue(14, 41)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getMappingValue(14) == 41
    tx = contract_instance.transact().pushStructureValue1(3)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getStructureValue1(0) == 3
    tx = contract_instance.transact().pushStructureArrayValue1(0, 11)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getStructureArrayValue1(0, 0) == 11
    tx = contract_instance.transact().pushStructureValue2(4)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getStructureValue2(0) == 4
    tx = contract_instance.transact().pushStructureArrayValue2(0, 12)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getStructureArrayValue2(0, 0) == 12

    # Can't upgrade to bad version
    with pytest.raises(TransactionFailed):
        tx = dispatcher.transact({'from': creator}).upgrade(contract2_bad_lib.address)
        chain.wait.for_receipt(tx)
    assert dispatcher.call().target().lower() == contract1_lib.address

    # Upgrade contract
    tx = dispatcher.transact({'from': creator}).upgrade(contract2_lib.address)
    chain.wait.for_receipt(tx)
    assert dispatcher.call().target().lower() == contract2_lib.address.lower()

    events = dispatcher.pastEvents('Upgraded').get()
    assert 2 == len(events)
    event_args = events[1]['args']
    assert contract1_lib.address.lower() == event_args['from'].lower()
    assert contract2_lib.address.lower() == event_args['to'].lower()
    assert creator == event_args['owner']

    # Check values after upgrade
    assert contract_instance.call().returnValue() == 20
    assert contract_instance.call().getStorageValue() == 5
    tx = contract_instance.transact().setStorageValue(5)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getStorageValue() == 10
    assert contract_instance.call().getArrayValueLength() == 2
    assert contract_instance.call().getArrayValue(0) == 12
    assert contract_instance.call().getArrayValue(1) == 232
    tx = contract_instance.transact().setMappingValue(13, 31)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getMappingValue(14) == 41
    assert contract_instance.call().getMappingValue(13) == 31
    tx = contract_instance.transact().pushStructureValue1(4)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getStructureValue1(0) == 3
    assert contract_instance.call().getStructureValue1(1) == 4
    tx = contract_instance.transact().pushStructureArrayValue1(0, 12)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getStructureArrayValue1(0, 0) == 11
    assert contract_instance.call().getStructureArrayValue1(0, 1) == 12
    tx = contract_instance.transact().pushStructureValue2(5)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getStructureValue2(0) == 4
    assert contract_instance.call().getStructureValue2(1) == 5
    tx = contract_instance.transact().pushStructureArrayValue2(0, 13)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getStructureArrayValue2(0, 0) == 12
    assert contract_instance.call().getStructureArrayValue2(0, 1) == 13

    # Changes ABI to ContractV2 for using additional methods
    contract_instance = web3.eth.contract(
        contract2_lib.abi,
        dispatcher.address,
        ContractFactoryClass=Contract)

    # Check new method and finish upgrade method
    assert contract_instance.call().storageValueToCheck() == 1
    tx = contract_instance.transact().setStructureValueToCheck2(0, 55)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getStructureValueToCheck2(0) == 55

    # Can't downgrade to first version due to storage
    with pytest.raises(TransactionFailed):
        tx = dispatcher.transact({'from': creator}).upgrade(contract1_lib.address)
        chain.wait.for_receipt(tx)

    # And can't upgrade to bad version
    with pytest.raises(TransactionFailed):
        tx = dispatcher.transact({'from': creator}).upgrade(contract2_bad_lib.address)
        chain.wait.for_receipt(tx)
    assert dispatcher.call().target().lower() == contract2_lib.address.lower()

    # But can rollback
    tx = dispatcher.transact({'from': creator}).rollback()
    chain.wait.for_receipt(tx)
    assert dispatcher.call().target().lower() == contract1_lib.address
    assert contract_instance.call().getArrayValueLength() == 2
    assert contract_instance.call().getArrayValue(0) == 12
    assert contract_instance.call().getArrayValue(1) == 232
    assert contract_instance.call().getStorageValue() == 1
    tx = contract_instance.transact().setStorageValue(5)
    chain.wait.for_receipt(tx)
    assert contract_instance.call().getStorageValue() == 5

    events = dispatcher.pastEvents('RolledBack').get()
    assert 1 == len(events)
    event_args = events[0]['args']
    assert contract2_lib.address.lower() == event_args['from'].lower()
    assert contract1_lib.address.lower() == event_args['to'].lower()
    assert creator == event_args['owner']

    # Can't upgrade to the bad version
    with pytest.raises(TransactionFailed):
        tx = dispatcher.transact({'from': creator}).upgrade(contract2_bad_lib.address)
        chain.wait.for_receipt(tx)
    assert dispatcher.call().target().lower() == contract1_lib.address.lower()

    # Check dynamically sized value
    # TODO uncomment after fixing dispatcher
    # tx = contract_instance.transact().setDynamicallySizedValue('Hola')
    # chain.wait.for_receipt(tx)
    # assert contract_instance.call().getDynamicallySizedValue() == 'Hola'

    # Create Event
    contract_instance = web3.eth.contract(
        contract1_lib.abi,
        dispatcher.address,
        ContractFactoryClass=Contract)
    tx = contract_instance.transact().createEvent(33)
    chain.wait.for_receipt(tx)
    events = contract_instance.pastEvents('EventV1').get()
    assert 1 == len(events)
    assert 33 == events[0]['args']['value']

    # Upgrade to version 3
    tx = dispatcher.transact({'from': creator}).upgrade(contract2_lib.address)
    chain.wait.for_receipt(tx)
    tx = dispatcher.transact({'from': creator}).upgrade(contract3_lib.address)
    chain.wait.for_receipt(tx)
    contract_instance = web3.eth.contract(
        contract2_lib.abi,
        dispatcher.address,
        ContractFactoryClass=Contract)
    assert dispatcher.call().target().lower() == contract3_lib.address.lower()
    assert contract_instance.call().returnValue() == 20
    assert contract_instance.call().getStorageValue() == 5
    assert contract_instance.call().getArrayValueLength() == 2
    assert contract_instance.call().getArrayValue(0) == 12
    assert contract_instance.call().getArrayValue(1) == 232
    assert contract_instance.call().getMappingValue(14) == 41
    assert contract_instance.call().getMappingValue(13) == 31
    assert contract_instance.call().getStorageValue() == 5
    assert contract_instance.call().getStructureValue1(0) == 3
    assert contract_instance.call().getStructureValue1(1) == 4
    assert contract_instance.call().getStructureArrayValue1(0, 0) == 11
    assert contract_instance.call().getStructureArrayValue1(0, 1) == 12
    assert contract_instance.call().getStructureValue2(0) == 4
    assert contract_instance.call().getStructureValue2(1) == 5
    assert contract_instance.call().getStructureArrayValue2(0, 0) == 12
    assert contract_instance.call().getStructureArrayValue2(0, 1) == 13
    assert contract_instance.call().getStructureValueToCheck2(0) == 55
    assert contract_instance.call().storageValueToCheck() == 2
    events = dispatcher.pastEvents('Upgraded').get()
    assert 4 == len(events)
    event_args = events[2]['args']
    assert contract1_lib.address.lower() == event_args['from'].lower()
    assert contract2_lib.address.lower() == event_args['to'].lower()
    assert creator == event_args['owner']
    event_args = events[3]['args']
    assert contract2_lib.address.lower() == event_args['from'].lower()
    assert contract3_lib.address.lower() == event_args['to'].lower()
    assert creator == event_args['owner']

    # Create and check events
    tx = contract_instance.transact().createEvent(22)
    chain.wait.for_receipt(tx)
    events = contract_instance.pastEvents('EventV2').get()
    assert 1 == len(events)
    assert 22 == events[0]['args']['value']
    contract_instance = web3.eth.contract(
        contract1_lib.abi,
        dispatcher.address,
        ContractFactoryClass=Contract)
    events = contract_instance.pastEvents('EventV1').get()
    assert 1 == len(events)
    assert 33 == events[0]['args']['value']
