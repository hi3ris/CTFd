// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// A Merkle-root airdrop. A claim is accepted if the sorted-pair keccak proof
/// of keccak256(abi.encodePacked(addr, amount)) hashes up to `root`. You are
/// given the full leaf set and the target claim (tree.json). The sealed bonus
/// is keyed by the proof you must construct.
contract MerkleAirdrop {
    bytes32 public immutable root;

    constructor(bytes32 _root) {
        root = _root;
    }

    function claim(
        address who,
        uint256 amount,
        bytes32[] calldata proof
    ) external view returns (bool) {
        bytes32 node = keccak256(abi.encodePacked(who, amount));
        for (uint256 i = 0; i < proof.length; i++) {
            bytes32 p = proof[i];
            node = node <= p
                ? keccak256(abi.encodePacked(node, p))
                : keccak256(abi.encodePacked(p, node));
        }
        return node == root;
    }
}
