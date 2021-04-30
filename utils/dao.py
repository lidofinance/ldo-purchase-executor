from utils.evm_script import encode_call_script, EMPTY_CALLSCRIPT


def create_vote(voting, token_manager, vote_desc, evm_script, tx_params):
    new_vote_script = encode_call_script([(
        voting.address,
        voting.newVote.encode_input(
            evm_script if evm_script is not None else EMPTY_CALLSCRIPT,
            vote_desc,
            False,
            False
        )
    )])
    tx = token_manager.forward(new_vote_script, tx_params)
    vote_id = tx.events['StartVote']['voteId']
    return (vote_id, tx)


def encode_token_transfer(token_address, recipient, amount, reference, finance):
    return (
        finance.address,
        finance.newImmediatePayment.encode_input(
            token_address,
            recipient,
            amount,
            reference
        )
    )


def encode_permission_grant(target_app, permission_name, grant_to, acl):
    permission_id = getattr(target_app, permission_name)()
    return (acl.address, acl.grantPermission.encode_input(grant_to, target_app, permission_id))


def encode_permission_revoke(target_app, permission_name, revoke_from, acl):
    permission_id = getattr(target_app, permission_name)()
    return (acl.address, acl.revokePermission.encode_input(revoke_from, target_app, permission_id))
