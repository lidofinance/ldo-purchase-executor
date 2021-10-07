# The deployment script for the contract on the Lido treasury Diversification Part 3
# https://research.lido.fi/t/lido-treasury-diversification-part-3/1059/1

import os
from brownie import accounts
from utils.config import get_is_live
from scripts.deploy import deploy

from purchase_config import (
    ETH_TO_LDO_RATE,
    VESTING_START_DELAY,
    VESTING_END_DELAY,
    OFFER_EXPIRATION_DELAY,
    LDO_PURCHASERS,
    ALLOCATIONS_TOTAL
)

def get_deployer_account():
    if not get_is_live():
        return accounts[0]

    if 'DEPLOYER' not in os.environ:
        raise EnvironmentError(
            'Please set DEPLOYER env variable to the deployer account name')

    return accounts.load(os.environ['DEPLOYER'])

def deploy_with_params(tx_params):
    executor = deploy(
        tx_params=tx_params,
        eth_to_ldo_rate=ETH_TO_LDO_RATE,
        vesting_start_delay=VESTING_START_DELAY,
        vesting_end_delay=VESTING_END_DELAY,
        offer_expiration_delay=OFFER_EXPIRATION_DELAY,
        ldo_purchasers=LDO_PURCHASERS,
        allocations_total=ALLOCATIONS_TOTAL
    )

    return executor

def main():
    return deploy_with_params({'from': get_deployer_account(), 'gas_price': '100 gwei'})
