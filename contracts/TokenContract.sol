// SPDX-License-Identifier: UNLICENSED

pragma solidity ^0.8.9;

import "./ERC20.sol";

contract TokenContract is ERC20 {
    address public contractOwner;

    constructor() ERC20("RewardToken", "RTK") {
        contractOwner = msg.sender;
    }

    function mint(address _address) public {
        require(msg.sender == contractOwner, "Only the contract owner (EPRO) can mint tokens");
        _mint(_address, 1000000);
    }
}