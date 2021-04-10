# LDO purchase executor

Allows a predefined list of addresses to purchase vested LDO tokens
from the DAO treasury in exchange for Ether at the predefined rate.
Implements the second approach (one-by-one) from
[the proposal](https://hackmd.io/@skozin/BkJR_UdSd):

Each participants can execute their part of the deal individually with individually assigned lock/vesting times based on time of the purchase. The opprtunity to participate expires in one month.

A `PurchaseExecutor` smart contract is deployed, having the following interface:

* `__init__(eth_to_ldo_rate: uint256, vesting_cliff_delay: uint256, vesting_end_delay: uint256, offer_expiration_delay: uint256, ldo_recipients: address[], ldo_allocations: uint256[])` initializes the contract and sets the immutable offer parameters.
* `execute_purchase_for(recipient: address): payable` will, if there's enough ETH for a purchase allocated to the `recipient` address, assign vested tokens to the recipient by calling the [`TokenManager.assignVested`] function, and send any ETH change back to the `msg.sender`. The vesting start is set to the timestamp of the block the transaction is included to. Reverts unless the `recipient` is a valid LDO recipient, the amount of ETH sent with the call is enough to purchase the whole amount of LDO allocated to the recipient, and the offer is still valid.
* `__default__(): payable` does `execute_purchase_for(msg.sender)`.

The process is the following:

1. The DAO votes for granting the [`ASSIGN_ROLE`] to the `PurchaseExecutor` smart contract and trasferring out 100_000_000 LDO. This allows the contract to transfer tokens from the DAO treasury to any address.
2. Each purchasers call the `PurchaseExecutor.execute_purchase_for` function, sending ETH and receiving the vested LDO tokens. The list of purchasers and their allocated amounts are set during the `PurchaseExecutor` contract deployment.
3. After the offer expires (in one month), `PurchaseExecutor.execute_purchase_for` always reverts. Unsold LDO tokens can be recovered to the DAO treasury by calling a permissionless function.

The contract: [contracts/PurchaseExecutor.vy](./contracts/PurchaseExecutor.vy)
