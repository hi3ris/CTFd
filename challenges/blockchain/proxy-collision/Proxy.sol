// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// Upgradeable proxy. State variables here occupy slots 0,1,2. It forwards
/// unknown calls to `implementation` via delegatecall, which runs the logic
/// contract's code against THIS contract's storage.
contract Proxy {
    address public implementation; // slot 0
    address public admin;          // slot 1
    bool public paused;            // slot 2

    fallback() external payable {
        address impl = implementation;
        assembly {
            calldatacopy(0, 0, calldatasize())
            let ok := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch ok
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
}
