pragma solidity ^0.4.25;
pragma experimental ABIEncoderV2;

import "./DeviceFactoryInterface.sol";
import "./Ownable.sol";


/**
 * @title Ereuse Device basic implementation
 */

contract DepositDevice is Ownable {
    // parameters -----------------------------------------------------------
    DeviceFactoryInterface factory;

    // types ----------------------------------------------------------------
    //Struct that mantains the basic values of the device
    struct DevData {
        string chid;
        string phid;
        string issuerID;
        uint registerDate;
        address owner;
        bool deregistered;
    }

    struct RegisterProofData {
        string chid;
        uint timestamp;
        uint blockNumber;
    }

    struct DeRegisterProofData {
        string chid;
        uint timestamp;
        uint blockNumber;
    }

    struct IssueProofData {
        string chid;
        string phid;
        string documentID;
        string documentSignature;
        string issuerID;
        uint timestamp;
        uint blockNumber;
    }

    // struct TransferProofData {
    //     address from;
    //     address to;
    //     string from_registrant;
    //     string to_registrant;
    //     uint timestamp;
    //     uint blockNumber;
    // }

    // struct RecycleProofData {
    //     uint timestamp;
    //     uint blockNumber;
    // }

    struct GenericProofData {
        string chid;
        string issuerID;
        string documentID;
        string documentSignature;
        string documentType;
        uint timestamp;
        uint blockNumber;
    }

    // variables -------------------------------------------------------------
    DevData data;
    RegisterProofData[] registerProofs;
    DeRegisterProofData[] deRegisterProofs; //shouldnt be a vector? it is for simplicity?
    IssueProofData[] issueProofs;
    //TransferProofData[] transferProofs;
    //RecycleProofData[] recycleProofs;
    GenericProofData[] genericProofs;

    // events ----------------------------------------------------------------
    event proofGenerated(bytes32 indexed proofHash);
    event registerProof(address deviceAddress, string chid, uint timestamp);
    event deRegisterProof(address deviceAddress, string chid, uint timestamp);
    event issueProof(address deviceAddress, string chid, string phid, string documentID, string documentSignature, string issuerID, uint timestamp);
    //event transferProof(address supplierAddress, address receiverAddress, address deviceAddress, uint timestamp);
    //event recycleProof(address userAddress, address deviceAddress, uint timestamp); 
    event genericProof(address deviceAddress, string chid, string issuerID, string documentID, string documentSignature, string documentType, uint timestamp);  
    //event DeviceTransferred(address deviceAddress, address new_owner, string new_registrant);
    event DeviceRecycled(address deviceAddress);

    constructor(
        string _chid,
        address _sender,
        address _factory
    ) public {
        factory = DeviceFactoryInterface(_factory);
        data.deregistered = false;
        data.owner = _sender;
        data.chid = _chid;
        data.registerDate = block.timestamp;
        _transferOwnership(_sender);

        RegisterProofData memory proof_data;
        proof_data.chid = _chid;
        proof_data.timestamp = block.timestamp;
        proof_data.blockNumber = block.number;
        generateRegisterProof(proof_data);
    }


    modifier registered() {
    require(data.deregistered == false, "This device is already deregistered");
    _;
  }

    function generateRegisterProof(RegisterProofData memory proof_data) internal {
        registerProofs.push(proof_data);
        emit registerProof(address(this), proof_data.chid, proof_data.timestamp);
    }

    function generateDeRegisterProof(DeRegisterProofData memory proof_data) internal {
        deRegisterProofs.push(proof_data);
        emit deRegisterProof(address(this), proof_data.chid, proof_data.timestamp);
    }
    
    function generateIssueProof(IssueProofData memory proof_data) internal {
        issueProofs.push(proof_data);
        emit issueProof(address(this), proof_data.chid, proof_data.phid, proof_data.documentID, proof_data.documentSignature, proof_data.issuerID, proof_data.timestamp);
    }

    //function emitGenericProof(GenericProofData memory proof_data) internal {
    //    genericProofs.push(proof_data);
    //    emit genericProof(address(this), proof_data.chid, proof_data.issuerID, proof_data.documentID, proof_data.documentSignature, proof_data.documentType, proof_data.timestamp);
    //}

    function issuePassport(string _chid, string _phid, string _documentID, string _documentSignature, string _issuerID) public onlyOwner registered{
        IssueProofData memory proof_data;
        proof_data.chid = _chid;
        proof_data.phid = _phid;
        proof_data.documentID = _documentID;
        proof_data.documentSignature = _documentSignature;
        proof_data.issuerID = _issuerID;
        proof_data.timestamp = block.timestamp;
        proof_data.blockNumber = block.number;

        data.chid = _chid;
        data.phid = _phid;
        data.issuerID = _issuerID;

        generateIssueProof(proof_data);
    }
    
    function generateGenericProof(string _deviceCHID, string _issuerID, string _documentID, string _documentSignature, string _documentType) public onlyOwner registered{
        GenericProofData memory proof_data;
        proof_data.chid = _deviceCHID;
        proof_data.issuerID = _issuerID;
        proof_data.documentID = _documentID;
        proof_data.documentSignature = _documentSignature;
        proof_data.documentType = _documentType;
        proof_data.timestamp = block.timestamp;
        proof_data.blockNumber = block.number;

        //emitGenericProof(proof_data);
        genericProofs.push(proof_data);
        emit genericProof(address(this), proof_data.chid, proof_data.issuerID, proof_data.documentID, proof_data.documentSignature, proof_data.documentType, proof_data.timestamp);
    }

    function deRegisterDevice(string _deviceCHID) public onlyOwner registered{
        data.deregistered = true;

        DeRegisterProofData memory proof_data;
        proof_data.chid = _deviceCHID;
        proof_data.timestamp = block.timestamp;
        proof_data.blockNumber = block.number;
        generateDeRegisterProof(proof_data);
    }

    // function issueDID(string _did, string _registerID, string _documentSignature) public onlyOwner{
    //     IssueProofData memory proof_data;
    //     proof_data.did = _did;
    //     proof_data.registerID = _registerID;
    //     proof_data.documentSignature = _documentSignature;
    //     proof_data.timestamp = block.timestamp;
    //     proof_data.blockNumber = block.number;

    //     data.did = _did;
    //     data.registerID = _registerID;

    //     generateIssueProof(proof_data);
    // }

    function getData() public view returns (DevData _data) {
        return data;
    }

    function getRegisterProofs() public view returns (RegisterProofData[] _data) {
        return registerProofs;
    }

    function getIssueProofs() public view returns (IssueProofData[] _data){
        return issueProofs;
    }

    function getGenericProofs() public view returns (GenericProofData[] _data){
        return genericProofs;
    }

    function getDeRegisterProofs() public view returns (DeRegisterProofData[] _data) {
        return deRegisterProofs;
    }


    //  function getTrasferProofs() public view returns (TransferProofData[] _data){
    //      return transferProofs;
    //  }

    //  function getRecycleProofs() public view returns (RecycleProofData[] _data){
    //      return recycleProofs;
    //  }

    // function generateTransferProof(TransferProofData memory proof_data) internal {
    //     transferProofs.push(proof_data);
    //     emit transferProof(proof_data.from, proof_data.to, address(this), proof_data.timestamp);
    // }

    //API DONE
    // function transferDevice(address _to, string _new_registrant)
    //     public
    //     onlyOwner
    // {
    //     TransferProofData memory proof_data;
    //     proof_data.from = data.owner;
    //     proof_data.to = _to;
    //     proof_data.from_registrant = data.registrantData;
    //     proof_data.to_registrant = _new_registrant;
    //     proof_data.timestamp = block.timestamp;
    //     proof_data.blockNumber = block.number;

    //     factory.transfer(data.owner, _to);
    //     data.owner = _to;
    //     data.registrantData = _new_registrant;
    //     if (owner != _to) transferOwnership(_to);

    //     generateTransferProof(proof_data);

    //     emit DeviceTransferred(address(this), data.owner, data.registrantData);
    // }

    // function generateRecycleProof(RecycleProofData memory proof_data) internal{
    //     recycleProofs.push(proof_data);
    //     emit recycleProof(data.owner, address(this), proof_data.timestamp);
    // }

    //API DONE
    // function recycle() public onlyOwner{
    //     factory.recycle(msg.sender);

    //     RecycleProofData memory proof_data;
    //     proof_data.timestamp = block.timestamp;
    //     proof_data.blockNumber = block.number;

    //     generateRecycleProof(proof_data);

    //     emit DeviceRecycled(address(this));
    // }



}