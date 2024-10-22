// SPDX-License-Identifier: AGPL-3.0-or-later

pragma solidity ^0.8.6;
pragma abicoder v2;


contract AccessList {

    struct Credential{
        address issuer;
        bool valid;
    }

    struct Actor{
        bool exists;
        Credential[] issuer_credentials;
        Credential[] operator_credentials;
        Credential[] witness_credentials;
        Credential[] verifier_credentials;
    }

    mapping(address => bool) issuers;
    mapping(address => bool) operators;
    mapping(address => bool) witnesses;
    mapping(address => bool) verifiers;
    mapping(address => Actor) actors;

    address trustAnchor;

    function registerActor(address _address) internal {
        if (!actors[_address].exists){
            actors[_address].exists = true;
        }
    }

    constructor(address _trustAnchor) {
        trustAnchor = _trustAnchor;
        registerActor(_trustAnchor);
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
            "Only usable by current Trust Anchor or an Issuer account"
        );
        _;
    }

    //Trust Anchor management
    function setTA(address _address) public TAnotSet {
        trustAnchor = _address;
        registerActor(_address);
    }

    function changeTA(address _address) public TAonly {
        trustAnchor = _address;
        registerActor(_address);
    }

    // //registers
    function registerIssuer(address _address) public TAIssuerOnly {
        issuers[_address] = true;
        registerActor(_address);
        Credential memory newCredential;
        newCredential.issuer = msg.sender;
        newCredential.valid = true;
        actors[_address].issuer_credentials.push(newCredential);
    }

    function registerOperator(address _address) public TAIssuerOnly {
        operators[_address] = true;
        registerActor(_address);
        Credential memory newCredential;
        newCredential.issuer = msg.sender;
        newCredential.valid = true;
        actors[_address].operator_credentials.push(newCredential);
    }

    function registerWitness(address _address) public TAIssuerOnly {
        witnesses[_address] = true;
        registerActor(_address);
        Credential memory newCredential;
        newCredential.issuer = msg.sender;
        newCredential.valid = true;
        actors[_address].witness_credentials.push(newCredential);
    }

    function registerVerifier(address _address) public TAIssuerOnly {
        verifiers[_address] = true;
        registerActor(_address);
        Credential memory newCredential;
        newCredential.issuer = msg.sender;
        newCredential.valid = true;
        actors[_address].verifier_credentials.push(newCredential);
    }

    //invalidates TODO add logic so this works with VC
    function invalidateIssuer(address _address) public TAonly {
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
    function checkIfIssuer(address _address) public view returns (bool result) {
        result = issuers[_address];
    }

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

    //outside world calls
    function get_issuer_credentials(address _address) public view returns (Credential memory credentials){
        return actors[_address].issuer_credentials[0];
    }
    function get_operator_credentials(address _address) public view returns (Credential memory credentials){
        return actors[_address].operator_credentials[0];
    }
    function get_witness_credentials(address _address) public view returns (Credential memory credentials){
        return actors[_address].witness_credentials[0];
    }
    function get_verifier_credentials(address _address) public view returns (Credential memory credentials){
        return actors[_address].verifier_credentials[0];
    }
}
