import pytest
from brownie import Wei, chain, reverts
from brownie.network.state import Chain

from purchase_config import ETH_TO_LDO_RATE_PRECISION

LDO_ALLOCATIONS = [
    1_000 * 10**18,
    3_000_000 * 10**18,
    20_000_000 * 10**18
]

# 100 LDO in one ETH
ETH_TO_LDO_RATE = 100 * 10**18

VESTING_CLIFF_DELAY = 1 * 60 * 60 * 24 * 365 # one year
VESTING_END_DELAY = 2 * 60 * 60 * 24 * 365 # two years
OFFER_EXPIRATION_DELAY = 2629746 # one month


@pytest.fixture(scope='function')
def executor(accounts, deploy_executor_and_pass_dao_vote):
    executor = deploy_executor_and_pass_dao_vote(
        eth_to_ldo_rate=ETH_TO_LDO_RATE,
        vesting_cliff_delay=VESTING_CLIFF_DELAY,
        vesting_end_delay=VESTING_END_DELAY,
        offer_expiration_delay=OFFER_EXPIRATION_DELAY,
        ldo_purchasers=[ (accounts[i], LDO_ALLOCATIONS[i]) for i in range(0, len(LDO_ALLOCATIONS)) ],
        allocations_total=sum(LDO_ALLOCATIONS)
    )
    executor.start({ 'from': accounts[0] })
    return executor


@pytest.fixture(scope='function')
def purchaser(accounts, executor, ldo_token):
    purchaser = accounts[0]
    purchase_ldo_amount = LDO_ALLOCATIONS[0]

    eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE
    executor.execute_purchase(purchaser, { 'from': purchaser, 'value': eth_cost })

    assert ldo_token.balanceOf(purchaser) > 0

    return purchaser


def test_transfer_not_allowed_before_vesting_start(executor, purchaser, stranger, ldo_token):
    with reverts():
        ldo_token.transfer(stranger, 1, {'from': purchaser})

    chain.sleep(VESTING_CLIFF_DELAY // 2)

    with reverts():
        ldo_token.transfer(stranger, 1, {'from': purchaser})

    chain.sleep(VESTING_CLIFF_DELAY // 2 - 10)

    with reverts():
        ldo_token.transfer(stranger, 1, {'from': purchaser})


def test_tokens_will_begin_becoming_transferable_linearly(executor, purchaser, stranger, ldo_token):
    chain.sleep(VESTING_CLIFF_DELAY + 60)
    ldo_token.transfer(stranger, 1, {'from': purchaser})

    vesting_duration = VESTING_END_DELAY - VESTING_CLIFF_DELAY
    chain.sleep(vesting_duration // 3)

    stranger_balance = ldo_token.balanceOf(stranger)
    purchaser_balance = ldo_token.balanceOf(purchaser)

    with reverts():
        ldo_token.transfer(stranger, purchaser_balance, {'from': purchaser})

    with reverts():
        ldo_token.transfer(stranger, purchaser_balance // 2, {'from': purchaser})

    ldo_token.transfer(stranger, purchaser_balance // 3 - 1, {'from': purchaser})

    assert ldo_token.balanceOf(purchaser) == purchaser_balance - purchaser_balance // 3 + 1
    assert ldo_token.balanceOf(stranger) == stranger_balance + purchaser_balance // 3 - 1

    chain.sleep(vesting_duration // 3)

    with reverts():
        ldo_token.transfer(stranger, ldo_token.balanceOf(purchaser), {'from': purchaser})

    ldo_token.transfer(stranger, purchaser_balance // 3 - 1, {'from': purchaser})

    assert ldo_token.balanceOf(purchaser) == purchaser_balance - 2 * purchaser_balance // 3 + 2
    assert ldo_token.balanceOf(stranger) == stranger_balance + 2 * purchaser_balance // 3 - 2


def test_vesting_will_end_after_vesting_end_delay(executor, purchaser, stranger, ldo_token):
    stranger_balance = ldo_token.balanceOf(stranger)
    purchaser_balance = ldo_token.balanceOf(purchaser)

    chain.sleep(VESTING_END_DELAY + 1)
    ldo_token.transfer(stranger, purchaser_balance, {'from': purchaser})

    assert ldo_token.balanceOf(purchaser) == 0
    assert ldo_token.balanceOf(stranger) == stranger_balance + purchaser_balance

