// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// A notes registry. You captured one raw transaction's calldata
/// (calldata.txt) plus this contract's ABI (abi.json). Decode the call to
/// recover the hidden `note` argument.
contract NotesRegistry {
    event Stored(uint256 id, address who, string note);

    function store(uint256 id, address who, string calldata note) external {
        emit Stored(id, who, note);
    }
}
