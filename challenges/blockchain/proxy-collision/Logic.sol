// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// The logic implementation. It declares `value` FIRST, so `value` lives in
/// slot 0 -- exactly where the Proxy keeps `implementation`. When called via
/// the proxy's delegatecall, setValue writes to the PROXY's slot 0.
contract Logic {
    uint256 public value;   // slot 0 (in proxy: collides with implementation)
    address public keeper;  // slot 1

    function setValue(uint256 v) external {
        value = v; // writes proxy slot 0 under delegatecall
    }
}
