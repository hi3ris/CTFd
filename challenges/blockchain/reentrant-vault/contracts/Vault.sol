// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Vault -- a naive ETH vault with a reentrancy bug (stage 1).
///
/// Users deposit ETH and can withdraw their balance. The bug: withdraw() sends
/// ETH to the caller BEFORE zeroing their recorded balance, so a contract that
/// re-enters withdraw() from its receive() hook is paid its balance again and
/// again until the vault is drained. This is the textbook
/// checks-effects-interactions violation.
///
/// The vault is seeded with other users' deposits, so draining it lets an
/// attacker walk away with far more than they put in. The win condition is the
/// effect: the vault's ETH balance reaching zero.
contract Vault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 bal = balances[msg.sender];
        require(bal > 0, "no balance");
        // INTERACTION before EFFECT: the external call happens while the
        // caller's recorded balance is still non-zero -> reentrancy.
        (bool ok, ) = msg.sender.call{value: bal}("");
        require(ok, "send failed");
        balances[msg.sender] = 0;
    }

    function vaultBalance() external view returns (uint256) {
        return address(this).balance;
    }

    // Accept seed funding from the deployer / other users.
    receive() external payable {
        balances[msg.sender] += msg.value;
    }
}
