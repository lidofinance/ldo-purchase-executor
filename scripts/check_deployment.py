import os
from brownie import accounts, interface, PurchaseExecutor

from utils.mainnet_fork import chain_snapshot, pass_and_exec_dao_vote
from utils.config import ldo_token_address, lido_dao_agent_address, get_is_live

from utils.config import (
    ldo_token_address,
    lido_dao_acl_address,
    lido_dao_token_manager_address,
    lido_dao_voting_address,
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

    executor_address = os.environ['EXECUTOR_ADDRESS']
    print(f'Using deployed executor at address {executor_address}')

    executor = PurchaseExecutor.at(executor_address)

    check_config(executor)
    check_allocations(executor)

    print(f'[ok] Executor is configured correctly')

    if get_is_live():
        print('Running on a live network, cannot check allocations reception.')
        print('Run on a mainnet fork to do this.')
        return

    with chain_snapshot():
        if 'VOTE_IDS' in os.environ:
          for vote_id in os.environ['VOTE_IDS'].split(','):
              pass_and_exec_dao_vote(int(vote_id))
        else:
            print('Force-configuring an executor without a vote')
            force_prepare_executor(executor)

        check_allocations_reception(executor)

    print(f'All good!')


def check_config(executor):
    print(f'ETHLDO rate: {ETH_TO_LDO_RATE / 10**18}')
    assert executor.eth_to_ldo_rate() == ETH_TO_LDO_RATE

    print(f'Offer expiration delay: {OFFER_EXPIRATION_DELAY / SEC_IN_A_DAY} days')
    assert executor.offer_expiration_delay() == OFFER_EXPIRATION_DELAY

    print(f'Vesting start delay: {VESTING_START_DELAY / SEC_IN_A_DAY} days')
    assert executor.vesting_start_delay() == VESTING_START_DELAY

    print(f'Vesting end delay: {VESTING_END_DELAY / SEC_IN_A_DAY} days')
    assert executor.vesting_end_delay() == VESTING_END_DELAY

    print(f'[ok] Global config is correct')


def check_allocations(executor):
    print(f'Total allocation: {ALLOCATIONS_TOTAL / 10**18} LDO')
    assert executor.ldo_allocations_total() == ALLOCATIONS_TOTAL

    for (purchaser, expected_allocation) in LDO_PURCHASERS:
        (allocation, eth_cost) = executor.get_allocation(purchaser)
        print(f'  {purchaser}: {expected_allocation / 10**18} LDO, {eth_cost} wei')
        expected_cost = expected_allocation * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE
        assert allocation == expected_allocation
        assert eth_cost == expected_cost

    print(f'[ok] Allocations are correct')

def force_prepare_executor(executor):
    # fund executor
    ldo_token = interface.ERC20(ldo_token_address)
    ldo_token.transfer(executor.address, ALLOCATIONS_TOTAL, {'from': lido_dao_agent_address})

    # grant executor ASSIGN_ROLE
    acl = interface.ACL(lido_dao_acl_address)
    token_manager = interface.TokenManager(lido_dao_token_manager_address)
    permission_id = getattr(token_manager, 'ASSIGN_ROLE')()
    acl.grantPermission(executor.address, token_manager, permission_id, {'from': lido_dao_voting_address})


def check_allocations_reception(executor):
    eth_banker = accounts.at('0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8', force=True)

    ldo_token = interface.ERC20(ldo_token_address)
    lido_dao_agent = interface.Agent(lido_dao_agent_address)
    executor_ldo_balance = ldo_token.balanceOf(executor.address)

    print(f'Executor LDO balance: {ALLOCATIONS_TOTAL / 10**18} LDO')
    assert executor_ldo_balance == ALLOCATIONS_TOTAL
    print('[ok] Executor fully funded')

    if not executor.offer_started():
        print(f'Starting the offer')
        executor.start({'from': accounts[0]})
        assert executor.offer_started()

    print('[ok] Offer started')


    print(f'Offer lasts {OFFER_EXPIRATION_DELAY / SEC_IN_A_DAY} days')
    assert executor.offer_expires_at() == executor.offer_started_at() + OFFER_EXPIRATION_DELAY

    print(f'Checking allocations reception')

    dao_agent_eth_balance_before = lido_dao_agent.balance()

    for i, (purchaser, expected_allocation) in enumerate(LDO_PURCHASERS):
        (allocation, eth_cost) = executor.get_allocation(purchaser)

        print(f'  {purchaser}: {expected_allocation / 10**18} LDO, {eth_cost} wei')

        assert allocation == expected_allocation

        purchaser_acct = accounts.at(purchaser, force=True)
        purchaser_eth_balance_before = purchaser_acct.balance()

        overpay = 10**17 * (i % 2)

        if purchaser_eth_balance_before < eth_cost + overpay:
            print(f'    funding the purchaser account with ETH...')
            eth_banker.transfer(to=purchaser, amount=(eth_cost + overpay - purchaser_eth_balance_before), silent=True)
            purchaser_eth_balance_before = eth_cost + overpay

        purchaser_ldo_balance_before = ldo_token.balanceOf(purchaser)

        print(f'    executing the purchase, overpay: {overpay / 10**18} ETH...')
        tx = purchaser_acct.transfer(to=executor, amount=(eth_cost + overpay), gas_limit=DIRECT_TRANSFER_GAS_LIMIT, silent=True)

        ldo_purchased = ldo_token.balanceOf(purchaser) - purchaser_ldo_balance_before
        eth_spent = purchaser_eth_balance_before - purchaser_acct.balance()

        assert ldo_purchased == allocation
        assert eth_spent == eth_cost
        print(f'    [ok] the purchase executed correctly, gas used: {tx.gas_used}')

    expected_total_eth_cost = ALLOCATIONS_TOTAL * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE
    total_eth_received = lido_dao_agent.balance() - dao_agent_eth_balance_before

    print(f'Total ETH received by the DAO: {expected_total_eth_cost}')
    assert total_eth_received == expected_total_eth_cost
    print(f'[ok] Total ETH received is correct')

    print(f'[ok] No LDO left on executor')
    assert ldo_token.balanceOf(executor.address) == 0

    print(f'[ok] No ETH left on executor')
    assert executor.balance() == 0
