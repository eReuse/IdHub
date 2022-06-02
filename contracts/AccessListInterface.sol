pragma solidity ^0.4.25;

contract AccessListInterface {
    mapping(address => bool) operators;
    mapping(address => bool) witnesses;
    mapping(address => bool) verifiers;
    address trustAnchor;
    
    //Trust Anchor management
    function setTA(address _address) public;
    function changeTA(address _address) public;
    //registers
    function registerOperator(address _address) public;
    function registerWitness(address _address) public;
    function registerVerifier(address _address) public;
    //invalidates
    function invalidateOperator(address _address) public;
    function invalidateWitness(address _address) public;
    function invalidateVerifier(address _address) public;
    //getters 
    function checkIfOperator(address _address) public view returns (bool result);
    function checkIfWitness(address _address) public view returns (bool result);
    function checkIfVerifier(address _address) public view returns (bool result);
    function checkTA() public view returns (address result);
}

