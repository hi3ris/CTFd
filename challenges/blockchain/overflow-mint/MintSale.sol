// SPDX-License-Identifier: MIT
pragma solidity 0.7.6; // pre-0.8: arithmetic is UNCHECKED by default

/// A token pre-sale. Buying `n` tokens costs `n * price` wei. Once your
/// balance reaches `WIN_TOKENS`, `claim()` unlocks the vault ciphertext by
/// XOR-ing it with keccak256(n) of the single buy that got you there.
///
/// You are given `sale.json` (price, budget, ciphertext) offline. Your wallet
/// holds only `budget` wei. Find the buy that wins.
contract MintSale {
    uint256 public constant price = 0x1000000000000000000000000000000000000000000000000000000000000001;
    uint256 public constant WIN_TOKENS = 256;
    mapping(address => uint256) public balances;

    function buy(uint256 n) external payable {
        // BUG: n * price can wrap around 2**256 for large n, so a huge token
        // count can be paid for with only a few wei.
        require(msg.value == n * price, "wrong payment");
        balances[msg.sender] += n;
    }

    function claim() external view returns (bytes memory) {
        require(balances[msg.sender] >= WIN_TOKENS, "not enough");
        // ... returns the ciphertext XOR keystream(keccak256(n)) ...
        return "";
    }
}
