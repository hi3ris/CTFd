// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// A hand-rolled ERC20. transferFrom moves tokens but FORGETS to reduce the
/// spender's allowance, so a single approval can be spent over and over.
/// You are given the victim's balance and your standing allowance
/// (token_state.json).
contract DriftToken {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function transferFrom(address from, address to, uint256 amount) external {
        require(balanceOf[from] >= amount, "balance");
        require(allowance[from][msg.sender] >= amount, "allowance");
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        // BUG: allowance[from][msg.sender] is never decremented here.
    }
}
