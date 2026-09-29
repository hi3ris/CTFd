// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// A "vault" deployed behind a thin proxy. It was meant to be initialized once
/// at deploy time, but the initializer is exposed and unguarded. The address
/// you control is 0x00000000000000000000000000000000A77aC6E5.
contract Vault {
    address public owner;
    bool private _init;
    bytes private sealed; // ciphertext of the vault note

    // BUG: no `initializer` guard, no owner check -> anyone can (re)claim it.
    function initialize(address newOwner) external {
        owner = newOwner;
    }

    modifier onlyOwner() {
        // BUG: tx.origin, not msg.sender.
        require(tx.origin == owner, "not owner");
        _;
    }

    /// Returns `sealed` XOR keystream(keccak256(msg.data of the winning
    /// initialize call)). You must reconstruct that exact calldata offline.
    function reveal() external view onlyOwner returns (bytes memory) {
        return sealed;
    }
}
