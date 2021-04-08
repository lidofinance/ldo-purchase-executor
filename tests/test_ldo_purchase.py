import pytest
from brownie import Wei, chain

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


@pytest.fixture(scope='module')
def executor(accounts, deploy_executor_and_pass_dao_vote):
    return deploy_executor_and_pass_dao_vote(
        eth_to_ldo_rate=ETH_TO_LDO_RATE,
        vesting_cliff_delay=VESTING_CLIFF_DELAY,
        vesting_end_delay=VESTING_END_DELAY,
        offer_expiration_delay=OFFER_EXPIRATION_DELAY,
        ldo_purchasers=[ (accounts[i], LDO_ALLOCATIONS[i]) for i in range(0, len(LDO_ALLOCATIONS)) ]
    )


def test_purchase_via_transfer(accounts, executor, dao_agent, helpers, ldo_token, dao_token_manager):
    purchaser = accounts.at(accounts[0], force=True)
    purchase_ldo_amount = LDO_ALLOCATIONS[0]

    eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

    allocation = executor.get_allocation(purchaser)
    assert allocation[0] == purchase_ldo_amount
    assert allocation[1] == eth_cost

    helpers.fund_with_eth(purchaser, eth_cost)

    dao_eth_balance_before = dao_agent.balance()

    tx = purchaser.transfer(to=executor, amount=eth_cost, gas_limit=400_000)
    purchase_evt = helpers.assert_single_event_named('PurchaseExecuted', tx)

    assert purchase_evt['ldo_receiver'] == purchaser
    assert purchase_evt['ldo_allocation'] == purchase_ldo_amount
    assert purchase_evt['eth_cost'] == eth_cost

    dao_eth_balance_increase = dao_agent.balance() - dao_eth_balance_before
    assert dao_eth_balance_increase == eth_cost
    assert ldo_token.balanceOf(purchaser) == purchase_ldo_amount

    vesting = dao_token_manager.getVesting(purchaser, purchase_evt['vesting_id'])

    assert vesting['amount'] == purchase_ldo_amount
    assert vesting['start'] == tx.timestamp
    assert vesting['cliff'] == tx.timestamp + VESTING_CLIFF_DELAY
    assert vesting['vesting'] == tx.timestamp + VESTING_END_DELAY
    assert vesting['revokable'] == False
