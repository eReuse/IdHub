// SPDX-License-Identifier: AGPL-3.0-or-later

pragma solidity ^0.8.6;

//import "project:/contracts/DocumentProofsInterface.sol";
//import "./DocumentProofsInterface.sol";


contract DocumentProofs {
    struct StampData{
        uint256 timestamp;
        bool stamp;
    }
    mapping(string => StampData) documents;

    event stampProof(string _hash, uint256 timestamp);
    //API DONE
    function stampDocument(string calldata _hash) public{
        StampData memory stamp_data;
        stamp_data.timestamp = block.timestamp;
        stamp_data.stamp = true;
        documents[_hash] = stamp_data;
        emit stampProof(_hash, stamp_data.timestamp);
    }
    //API DONE
    function checkStamp(string calldata _hash) public view returns(bool b){
        if(documents[_hash].stamp == true) return true;
    }
}
