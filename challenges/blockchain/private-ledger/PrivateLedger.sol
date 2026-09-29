// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// A minimal on-chain ledger. The player is given a raw dump of this
/// contract's storage (slot -> 32-byte word). The address you control is
/// 0x00000000000000000000000000000000c0FFee01.
contract PrivateLedger {
    address public owner;                          // slot 0
    uint256 public totalDeposits;                  // slot 1
    uint256 private depositNonce;                  // slot 2
    mapping(address => uint256) public balances;   // slot 3
    mapping(address => bytes32) private vaultNotes; // slot 4

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
        depositNonce += 1;
    }

    // Notes are private on purpose. Only the ledger keeper is meant to read
    // them back through an off-chain view. There is no public getter.
    function _setNote(address who, bytes32 note) internal {
        vaultNotes[who] = note;
    }
}
