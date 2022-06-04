pragma solidity ^0.4.25;

contract AccessList {
    mapping(address => bool) issuers;
    mapping(address => bool) operators;
    mapping(address => bool) witnesses;
    mapping(address => bool) verifiers;

    address trustAnchor;

    constructor(address _trustAnchor) public {
        trustAnchor = _trustAnchor;
    }

    modifier TAnotSet() {
        require(
            trustAnchor == address(0),
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

    modifier TAIssuerOnly() {
        require(
            (trustAnchor == msg.sender ||
            issuers[msg.sender]),
            "Only usable by current Trust Anchor account"
        );
        _;
    }

    //Trust Anchor management
    function setTA(address _address) public TAnotSet {
        trustAnchor = _address;
    }

    function changeTA(address _address) public TAonly {
        trustAnchor = _address;
    }

    //registers
    function registerIssuer(address _address) public TAOnly {
        issuers[_address] = true;
    }

    function registerOperator(address _address) public TAIssuerOnly {
        operators[_address] = true;
    }

    function registerWitness(address _address) public TAIssuerOnly {
        witnesses[_address] = true;
    }

    function registerVerifier(address _address) public TAIssuerOnly {
        verifiers[_address] = true;
    }

    //invalidates
    function invalidateIssuer(address _address) public TAOnly {
        issuers[_address] = false;
    }

    function invalidateOperator(address _address) public TAIssuerOnly {
        operators[_address] = false;
    }

    function invalidateWitness(address _address) public TAIssuerOnly {
        witnesses[_address] = false;
    }

    function invalidateVerifier(address _address) public TAIssuerOnly {
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
