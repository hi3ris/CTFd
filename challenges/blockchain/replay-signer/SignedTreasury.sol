// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// A withdrawal authorizer. Each request is an ECDSA signature over
/// keccak256(message) by `signer`. You captured two signed requests
/// (signatures.json). The vault note is sealed with the signer's private key.
contract SignedTreasury {
    address public immutable signer;

    constructor(address _signer) {
        signer = _signer;
    }

    function withdraw(bytes32 h, uint8 v, bytes32 r, bytes32 s) external view {
        require(ecrecover(h, v, r, s) == signer, "bad sig");
        // ... pays out ...
    }
}
