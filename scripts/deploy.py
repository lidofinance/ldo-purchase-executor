from brownie import ZERO_ADDRESS, accounts

try:
    from brownie import PurchaseExecutor, interface
except ImportError:
    print(
        "You're probably running inside Brownie console. Please call `set_console_globals`, "
        "passing `interface` and `PurchaseExecutor` global variables"
    )
    pass


def set_console_globals(**kwargs):
    global PurchaseExecutor
    global interface
    PurchaseExecutor = kwargs['PurchaseExecutor']
    interface = kwargs['interface']


from utils.dao import (
    create_vote,
    encode_token_transfer,
    encode_permission_grant,
    encode_permission_revoke,
    encode_call_script
)

from utils.config import (
    ldo_token_address,
    lido_dao_acl_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_token_manager_address
)

from purchase_config import (
    ETH_TO_LDO_RATE,
    VESTING_CLIFF_DELAY,
    VESTING_END_DELAY,
    OFFER_EXPIRATION_DELAY,
    LDO_PURCHASERS,
    ALLOCATIONS_TOTAL
)


def propose_vesting_manager_contract(
    manager_address,
    total_ldo_amount,
    ldo_transfer_reference,
    tx_params
):
    acl = interface.ACL(lido_dao_acl_address)
    voting = interface.Voting(lido_dao_voting_address)
    finance = interface.Finance(lido_dao_finance_address)
    token_manager = interface.TokenManager(lido_dao_token_manager_address)

    evm_script = encode_call_script([
        encode_token_transfer(
            token_address=ldo_token_address,
            recipient=manager_address,
            amount=total_ldo_amount,
            reference=ldo_transfer_reference,
            finance=finance
        ),
        encode_permission_grant(
            target_app=token_manager,
            permission_name='ASSIGN_ROLE',
            grant_to=manager_address,
            acl=acl
        )
    ])
    return create_vote(
        voting=voting,
        token_manager=token_manager,
        vote_desc=f'Make {manager_address} a vesting manager for total {total_ldo_amount} LDO',
        evm_script=evm_script,
        tx_params=tx_params
    )


def propose_replacement_vesting_manager_contract(
    prev_manager_address,
    new_manager_address,
    total_ldo_amount,
    ldo_transfer_reference,
    tx_params
):
    acl = interface.ACL(lido_dao_acl_address)
    voting = interface.Voting(lido_dao_voting_address)
    finance = interface.Finance(lido_dao_finance_address)
    token_manager = interface.TokenManager(lido_dao_token_manager_address)

    evm_script = encode_call_script([
        encode_permission_revoke(
            target_app=token_manager,
            permission_name='ASSIGN_ROLE',
            revoke_from=prev_manager_address,
            acl=acl
        ),
        encode_token_transfer(
            token_address=ldo_token_address,
            recipient=new_manager_address,
            amount=total_ldo_amount,
            reference=ldo_transfer_reference,
            finance=finance
        ),
        encode_permission_grant(
            target_app=token_manager,
            permission_name='ASSIGN_ROLE',
            grant_to=new_manager_address,
            acl=acl
        )
    ])
    return create_vote(
        voting=voting,
        token_manager=token_manager,
        vote_desc=f'Change vesting manager for total {total_ldo_amount} LDO from {prev_manager_address} to {new_manager_address}',
        evm_script=evm_script,
        tx_params=tx_params
    )


def deploy(
    tx_params,
    eth_to_ldo_rate,
    vesting_cliff_delay,
    vesting_end_delay,
    offer_expiration_delay,
    ldo_purchasers,
    allocations_total
):
    zero_padding_len = 50 - len(ldo_purchasers)
    ldo_recipients = [ p[0] for p in ldo_purchasers ] + [ZERO_ADDRESS] * zero_padding_len
    ldo_allocations = [ p[1] for p in ldo_purchasers ] + [0] * zero_padding_len

    return PurchaseExecutor.deploy(
        eth_to_ldo_rate,
        vesting_cliff_delay,
        vesting_end_delay,
        offer_expiration_delay,
        ldo_recipients,
        ldo_allocations,
        allocations_total,
        tx_params
    )


def deploy_and_start_dao_vote(
    tx_params,
    eth_to_ldo_rate=ETH_TO_LDO_RATE,
    vesting_cliff_delay=VESTING_CLIFF_DELAY,
    vesting_end_delay=VESTING_END_DELAY,
    offer_expiration_delay=OFFER_EXPIRATION_DELAY,
    ldo_purchasers=LDO_PURCHASERS,
    allocations_total = ALLOCATIONS_TOTAL
):
    executor = deploy(
        tx_params=tx_params,
        eth_to_ldo_rate=eth_to_ldo_rate,
        vesting_cliff_delay=vesting_cliff_delay,
        vesting_end_delay=vesting_end_delay,
        offer_expiration_delay=offer_expiration_delay,
        ldo_purchasers=ldo_purchasers,
        allocations_total=allocations_total
    )

    (vote_id, _) = propose_vesting_manager_contract(
        manager_address=executor.address,
        total_ldo_amount=allocations_total,
        ldo_transfer_reference=f"Transfer LDO tokens to be sold for ETH",
        tx_params=tx_params
    )

    return (executor, vote_id)


def deploy_replacement_executor_and_start_dao_vote(
    tx_params,
    prev_executor_address,
    eth_to_ldo_rate=ETH_TO_LDO_RATE,
    vesting_cliff_delay=VESTING_CLIFF_DELAY,
    vesting_end_delay=VESTING_END_DELAY,
    offer_expiration_delay=OFFER_EXPIRATION_DELAY,
    ldo_purchasers=LDO_PURCHASERS,
    allocations_total=ALLOCATIONS_TOTAL
):
    executor = deploy(
        tx_params=tx_params,
        eth_to_ldo_rate=eth_to_ldo_rate,
        vesting_cliff_delay=vesting_cliff_delay,
        vesting_end_delay=vesting_end_delay,
        offer_expiration_delay=offer_expiration_delay,
        ldo_purchasers=ldo_purchasers,
        allocations_total=allocations_total
    )

    (vote_id, _) = propose_replacement_vesting_manager_contract(
        prev_manager_address=prev_executor_address,
        new_manager_address=executor.address,
        total_ldo_amount=allocations_total,
        ldo_transfer_reference=f"Transfer LDO tokens to be sold for ETH",
        tx_params=tx_params
    )

    return (executor, vote_id)
