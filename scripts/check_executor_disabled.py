import os
import sys
import brownie
from brownie import chain, network, accounts, Wei, interface, PurchaseExecutor

from utils.mainnet_fork import chain_snapshot, pass_and_exec_dao_vote

from utils.config import (
    ldo_token_address,
    lido_dao_agent_address,
    lido_dao_voting_address,
    get_is_live
)

from purchase_config import (
    ETH_TO_LDO_RATE_PRECISION,
    ETH_TO_LDO_RATE,
    VESTING_START_DELAY,
    VESTING_END_DELAY,
    OFFER_EXPIRATION_DELAY,
    LDO_PURCHASERS,
    ALLOCATIONS_TOTAL
)


DIRECT_TRANSFER_GAS_LIMIT = 400_000
SEC_IN_A_DAY = 60 * 60 * 24


def main():
    if 'EXECUTOR_ADDRESS' not in os.environ:
        raise EnvironmentError('Please set the EXECUTOR_ADDRESS environment variable')

    if get_is_live():
        print('Running on a live network, cannot check. Please run on a mainnet fork.')
        return

    with chain_snapshot():
        run_checks()


def run_checks():
    executor_address = os.environ['EXECUTOR_ADDRESS']
    print(f'Using the deployed executor at address {executor_address}')

    if 'VOTE_IDS' in os.environ:
        for vote_id in os.environ['VOTE_IDS'].split(','):
            pass_and_exec_dao_vote(int(vote_id))

    executor = PurchaseExecutor.at(executor_address)

    print(f'Checking that executor {executor_address} is disabled')

    check_executor_disabled(executor)

    print(f'All good!')


def check_executor_disabled(executor):
    eth_banker = accounts.at('0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8', force=True)
    ldo_token = interface.ERC20(ldo_token_address)
    lido_dao_agent = interface.Agent(lido_dao_agent_address)

    if not executor.offer_started():
        print(f'Starting the offer')
        executor.start({'from': accounts[0], 'silent': True})
        assert executor.offer_started()

    print('[ok] Offer started')

    allocations_total = executor.ldo_allocations_total()
    executor_ldo_balance = ldo_token.balanceOf(executor.address)

    print(f'Total allocation: {allocations_total / 10**18}')
    print(f'Executor LDO balance: {executor_ldo_balance / 10**18}')

    if allocations_total == executor_ldo_balance:
        print('[ok] Executor fully funded')
    else:
        print('[WARN] Some executors have executed their purchase')

    print(f'Checking inability to purchase allocations')

    executed_purchasers = []

    for i, (purchaser, expected_allocation) in enumerate(LDO_PURCHASERS):
        (allocation, eth_cost) = executor.get_allocation(purchaser)

        print(f'  {purchaser}: {allocation / 10**18} LDO, {eth_cost} wei')

        if allocation == 0:
            executed_purchasers = executed_purchasers + [purchaser]
            print(f'    [WARN] purchaser {purchaser} has executed the purchase')
            continue

        purchaser_acct = accounts.at(purchaser, force=True)
        purchaser_eth_balance = purchaser_acct.balance()

        if purchaser_eth_balance < eth_cost:
            print(f'    funding the purchaser account with ETH...')
            eth_banker.transfer(to=purchaser, amount=(eth_cost - purchaser_eth_balance), silent=True)

        try:
            print(f'    attempting to execute the purchase...')
            purchaser_acct.transfer(to=executor, amount=eth_cost, gas_limit=DIRECT_TRANSFER_GAS_LIMIT, silent=True)
            raise AssertionError('purchase succeeded')
        except brownie.exceptions.VirtualMachineError as err:
            print(f'    [ok] purchase reverted: {err}')

    delay = executor.offer_expiration_delay()

    print(f'Checking that tokens will be transferred back after {delay / SEC_IN_A_DAY} days')

    chain.sleep(delay)
    chain.mine()
    assert executor.offer_expired()

    agent_ldo_balance_before = ldo_token.balanceOf(lido_dao_agent)
    print(f'Agent balance before: {agent_ldo_balance_before / 10**18}')

    print('Recovering unsold tokens...')
    executor.recover_unsold_tokens({'from': accounts[0], 'silent': True})

    agent_ldo_balance_after = ldo_token.balanceOf(lido_dao_agent)
    print(
        f'Agent balance after: {agent_ldo_balance_after / 10**18} '
        f'(change: {(agent_ldo_balance_after - agent_ldo_balance_before) / 10**18})'
    )

    assert agent_ldo_balance_after - agent_ldo_balance_before == executor_ldo_balance

    print('[ok] Remaining allocation was recovered')

    if len(executed_purchasers) == 0:
        print('[ok] No purchasers executed the purchase')
    else:
        print('[WARN] Some purchasers have executed the purchase:')
        for addr in executed_purchasers:
            print(f'       {addr}')
        raise AssertionError('some purchasers have executed the purchase')
