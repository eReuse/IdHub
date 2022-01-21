pragma solidity ^0.4.25;

contract DocumentProofsInterface {
    struct StampData{
        uint256 timestamp;
        bool stamp;
    }
    mapping(string => StampData) documents;

    function stampDocument(string _hash) public;
    function checkStamp(string _hash) 
    public view
    returns(bool b);
}
