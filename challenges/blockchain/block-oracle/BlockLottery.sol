// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// A lottery that draws its "random" winning ticket from block context. The
/// winner takes the sealed pot. You are given the exact block context of the
/// draw (draw.json).
contract BlockLottery {
    bytes private pot; // sealed with keystream(keccak256(winningTicket))

    function draw() public view returns (uint256) {
        // BUG: fully deterministic given the block header -- not random.
        return
            uint256(
                keccak256(
                    abi.encodePacked(
                        block.timestamp,
                        block.number,
                        block.prevrandao
                    )
                )
            );
    }

    function claim(uint256 guess) external view returns (bytes memory) {
        require(guess == draw(), "not the winner");
        return pot;
    }
}
