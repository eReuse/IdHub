pragma solidity ^0.4.25;

contract AddressRoles {
    mapping(address => bool) operators;
    mapping(address => bool) witnesses;
    mapping(address => bool) verifiers;

    address trustAnchor;

    modifier TAnotSetted() {
        require(
            trustAnchor == 0x0000000000000000000000000000000000000000,
            "A Trust Anchor account is already in use."
        );
        _;
    }

    modifier TAonly() {
        require(
            trustAnchor == msg.sender,
            "Only usable by current Trust Anchor account"
        );
        _;
    }

    // modifier onlyOp() {
    //     require(checkIfOperator(msg.sender) == true, "The message sender is not an operator");
    //     _;
    // }

    // modifier onlyOpWit() {
    //     require((checkIfOperator(msg.sender) == true || checkIfWitness(msg.sender) == true), "The message sender is not an operator or witness");
    //     _;
    // }


    //Trust Anchor management
    function setTA(address _address) public TAnotSetted {
        trustAnchor = _address;
    }

    function changeTA(address _address) public TAonly {
        trustAnchor = _address;
    }

    //registers
    function registerOperator(address _address) public TAonly {
        operators[_address] = true;
    }

    function registerWitness(address _address) public TAonly {
        witnesses[_address] = true;
    }

    function registerVerifier(address _address) public TAonly {
        verifiers[_address] = true;
    }

    //invalidates
    function invalidateOperator(address _address) public TAonly {
        operators[_address] = false;
    }

    function invalidateWitness(address _address) public TAonly {
        witnesses[_address] = false;
    }

    function invalidateVerifier(address _address) public TAonly {
        verifiers[_address] = false;
    }

    //getters. Could be internal since they are used by modifiers
    function checkIfOperator(address _address) public view returns (bool result) {
        result = operators[_address];
    }

    function checkIfWitness(address _address) public view returns (bool result) {
        result = witnesses[_address];
    }

    function checkIfVerifier(address _address) public view returns (bool result) {
        result = verifiers[_address];
    }

    function checkTA() public view returns (address result) {
        result = trustAnchor;
    }
}
