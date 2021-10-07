import os
from brownie import PurchaseExecutor

from utils.mainnet_fork import chain_snapshot, pass_and_exec_dao_vote
from utils.config import get_is_live

from purchase_config import (
    ETH_TO_LDO_RATE_PRECISION,
    ETH_TO_LDO_RATE,
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
    old_executor = PurchaseExecutor.at('0x489f04eeff0ba8441d42736549a1f1d6cca74775')

    check_config_equals_old_one(executor, old_executor)
    check_allocations_equal_old_ones(executor, old_executor)

    print(f'[ok] Executor is configured correctly')

    if get_is_live():
        print('Running on a live network, cannot check allocations reception.')
        print('Run on a mainnet fork to do this.')
        return

    with chain_snapshot():
        if 'VOTE_IDS' in os.environ:
            for vote_id in os.environ['VOTE_IDS'].split(','):
                pass_and_exec_dao_vote(int(vote_id))

    print(f'All good!')


def check_config_equals_old_one(executor, old_executor):
    print(f'Previous ETHLDO rate: {old_executor.eth_to_ldo_rate()}')
    assert executor.eth_to_ldo_rate() == old_executor.eth_to_ldo_rate()

    print(f'Previous Offer expiration delay: {old_executor.offer_expiration_delay()} days')
    assert executor.offer_expiration_delay() == old_executor.offer_expiration_delay()

    print(f'Previous Vesting start delay: {old_executor.vesting_start_delay()} days')
    assert executor.vesting_start_delay() == old_executor.vesting_start_delay()

    print(f'Previous Vesting end delay: {old_executor.vesting_end_delay()} days')
    assert executor.vesting_end_delay() == old_executor.vesting_end_delay()

    print(f'[ok] Global config is correct')


def check_allocations_equal_old_ones(executor, old_executor):
    print(f'Total allocation: {ALLOCATIONS_TOTAL / 10**18} LDO')
    assert executor.ldo_allocations_total() == ALLOCATIONS_TOTAL

    sum_old_allocations = 0

    for (purchaser, expected_allocation) in LDO_PURCHASERS:
        (allocation, eth_cost) = executor.get_allocation(purchaser)
        (old_allocation, old_eth_cost) = old_executor.get_allocation(purchaser)
        print(f'  {purchaser}: {expected_allocation / 10**18} LDO, {eth_cost} wei')
        expected_cost = expected_allocation * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE
        sum_old_allocations = sum_old_allocations + allocation
        assert allocation == expected_allocation
        assert allocation == old_allocation
        assert eth_cost == expected_cost
        assert eth_cost == old_eth_cost

    assert executor.ldo_allocations_total() == sum_old_allocations

    print(f'[ok] Allocations are correct')
