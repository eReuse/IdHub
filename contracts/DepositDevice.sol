pragma solidity ^0.8.6;
//pragma experimental ABIEncoderV2;
pragma abicoder v2;

import "./DeviceFactory.sol";
import "./Ownable.sol";
import "./AccessList.sol";
import "./TokenContract.sol";

/**
 * @title Ereuse Device basic implementation
 */

contract DepositDevice is Ownable {
    // parameters -----------------------------------------------------------
    DeviceFactory factory;
    AccessList roles;
    TokenContract token_contract;
    // types ----------------------------------------------------------------
    //Struct that mantains the basic values of the device
    struct DevData {
        string chid;
        string phid;
        uint registerDate;
        address owner;
        bool deregistered;
    }

    // struct RegisterProofData {
    //     string chid;
    //     uint timestamp;
    //     uint blockNumber;
    // }

    struct DeRegisterProofData {
        string chid;
        uint timestamp;
        uint blockNumber;
    }

    struct TransferProofData {
        address from;
        address to;
        // string from_registrant;
        // string to_registrant;
        uint timestamp;
        uint blockNumber;
    }

    // struct RecycleProofData {
    //     uint timestamp;
    //     uint blockNumber;
    // }

    struct GenericProofData {
        string chid;
        string phid;
        address issuerID;
        string inventoryID;
        string documentHashAlgorithm;
        string documentHash;
        string documentType;
        uint timestamp;
        uint blockNumber;
    }

    struct Service {
        string endpoint;
        string type_;
        string description;
        string fragment;
    }

    struct DidData {
        address contractAddress;
        address controller;
        string chid;
        Service[] services;
        uint chainid;
    }

    // variables -------------------------------------------------------------
    DevData data;
    // RegisterProofData[] registerProofs;
    DeRegisterProofData[] deRegisterProofs; //shouldnt be a vector? it is for simplicity?
    string[] phids;
    TransferProofData[] transferProofs;
    //RecycleProofData[] recycleProofs;
    GenericProofData[] genericProofs;
    Service[] services;

    // events ----------------------------------------------------------------
    event proofGenerated(bytes32 indexed proofHash);
    // event registerProof(address deviceAddress, string chid, uint timestamp);
    event deRegisterProof(address deviceAddress, string chid, uint timestamp);
    // event issueProof(address deviceAddress, string chid, string phid, string documentID, string documentSignature, string issuerID, uint timestamp);
    event transferProof(address supplierAddress, address receiverAddress, address deviceAddress, uint timestamp);
    //event recycleProof(address userAddress, address deviceAddress, uint timestamp); 
    event genericProof(address deviceAddress, string chid, string phid, address issuerID, string documentHashAlgorithm, string documentHash, string documentType, uint timestamp, string inventoryID);  
    //event DeviceTransferred(address deviceAddress, address new_owner, string new_registrant);
    event DeviceRecycled(address deviceAddress);
    event fundsReleased(address verifierAddress, address receiverAddress);

    constructor(
        string memory _chid,
        address _sender,
        address _factory,
        address _roles,
        string memory _documentHashAlgorithm,
        string memory _documentHash,
        string memory _inventoryID,
        address _tokenContract
    ) {
        factory = DeviceFactory(_factory);
        roles = AccessList(_roles);
        token_contract = TokenContract(_tokenContract);
        data.deregistered = false;
        data.owner = _sender;
        data.chid = _chid;
        data.registerDate = block.timestamp;
        _transferOwnership(_sender);

        // RegisterProofData memory proof_data;
        // proof_data.chid = _chid;
        // proof_data.timestamp = block.timestamp;
        // proof_data.blockNumber = block.number;
        // generateRegisterProof(proof_data);

        _generateGenericProof(_sender, _documentHashAlgorithm, _documentHash, "Device_creation", _inventoryID);
    }

    modifier onlyOpWitVer() {
        require((owner == msg.sender || 
        roles.checkIfOperator(msg.sender) == true || 
        roles.checkIfWitness(msg.sender) == true || 
        roles.checkIfVerifier(msg.sender) == true), "The message sender is not an owner, operator, verifier or witness");
        _;
    }

    modifier onlyOpWit() {
        require((owner == msg.sender || 
        roles.checkIfOperator(msg.sender) == true || 
        roles.checkIfWitness(msg.sender) == true), "The message sender is not an owner, operator or witness");
        _;
    }

    modifier onlyOp() {
        require((owner == msg.sender || 
        roles.checkIfOperator(msg.sender) == true), "The message sender is not an owner or operator");
        _;
    }

    modifier onlyVer() {
        require((roles.checkIfVerifier(msg.sender) == true), "The message sender is not a verifier");
        _;
    }


    modifier registered() {
    require(data.deregistered == false, "This device is already deregistered");
    _;
    }

    // function generateRegisterProof(RegisterProofData memory proof_data) internal {
    //     registerProofs.push(proof_data);
    //     emit registerProof(address(this), proof_data.chid, proof_data.timestamp);
    // }

    function generateDeRegisterProof(DeRegisterProofData memory proof_data) internal {
        deRegisterProofs.push(proof_data);
        emit deRegisterProof(address(this), proof_data.chid, proof_data.timestamp);
    }
    
    // function generateIssueProof(IssueProofData memory proof_data) internal {
    //     issueProofs.push(proof_data);
    //     emit issueProof(address(this), proof_data.chid, proof_data.phid, proof_data.documentID, proof_data.documentSignature, proof_data.issuerID, proof_data.timestamp);
    // }

    //function emitGenericProof(GenericProofData memory proof_data) internal {
    //    genericProofs.push(proof_data);
    //    emit genericProof(address(this), proof_data.chid, proof_data.issuerID, proof_data.documentID, proof_data.documentSignature, proof_data.documentType, proof_data.timestamp);
    //}

    function issuePassport(string calldata _phid, string calldata _documentHashAlgorithm, string calldata _documentHash, string calldata _inventoryID) public registered onlyOpWit{
        phids.push(_phid);

        data.phid = _phid;

        // generateIssueProof(proof_data);

        _generateGenericProof(msg.sender, _documentHashAlgorithm, _documentHash, "DPP_creation", _inventoryID);
    }
    
    function generateGenericProof(string calldata _documentHashAlgorithm, string calldata _documentHash, string calldata _documentType, string calldata _inventoryID) public registered onlyOpWit{
        _generateGenericProof(msg.sender, _documentHashAlgorithm, _documentHash, _documentType, _inventoryID);   
    }

    function _generateGenericProof(address _sender, string memory _documentHashAlgorithm, string memory _documentHash, string memory _documentType, string memory _inventoryID) internal {
        GenericProofData memory proof_data;
        proof_data.chid = data.chid;
        proof_data.phid = data.phid;
        proof_data.issuerID = _sender;
        proof_data.documentHashAlgorithm = _documentHashAlgorithm;
        proof_data.documentHash = _documentHash;
        proof_data.documentType = _documentType;
        proof_data.timestamp = block.timestamp;
        proof_data.blockNumber = block.number;
        proof_data.inventoryID = _inventoryID;

        //emitGenericProof(proof_data);
        genericProofs.push(proof_data);
        emit genericProof(address(this), proof_data.chid, proof_data.phid, proof_data.issuerID, proof_data.documentHashAlgorithm, proof_data.documentHash, proof_data.documentType, proof_data.timestamp, proof_data.inventoryID);
    }

    function releaseFunds(address _recycler)public onlyVer{
        require(token_contract.transfer(_recycler, 100), "Already paid out.");
        _generateGenericProof(msg.sender, "", "", "Funds_released", "");
        emit fundsReleased(msg.sender, _recycler);
    }
    

    function deRegisterDevice(string calldata _deviceCHID) public registered onlyOp{
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

    function getData() onlyOpWitVer public view returns (DevData memory _data) {
        return data;
    }

    // function getRegisterProofs() public view onlyOpWitVer returns (RegisterProofData[] memory _data) {
    //     return registerProofs;
    // }

    // function getIssueProofs() public view onlyOpWitVer returns (IssueProofData[] memory _data){
    //     return issueProofs;
    // }
    function getDPPs() public view returns (string[] memory _data){
        return phids;
    }

    function getGenericProofs() onlyOpWitVer public view returns (GenericProofData[] memory _data){
        return genericProofs;
    }

    function getDeRegisterProofs() onlyOpWitVer public view returns (DeRegisterProofData[] memory _data) {
        return deRegisterProofs;
    }

     function getTrasferProofs() onlyOpWitVer public view  returns (TransferProofData[] memory _data){
         return transferProofs;
     }

    //  function getRecycleProofs() public view returns (RecycleProofData[] _data){
    //      return recycleProofs;
    //  }

    function generateTransferProof(TransferProofData memory proof_data) internal {
        transferProofs.push(proof_data);
        emit transferProof(proof_data.from, proof_data.to, address(this), proof_data.timestamp);
    }

    //API DONE
    function transferDevice(address _to)
        public
        onlyOwner
    {
        TransferProofData memory proof_data;
        proof_data.from = data.owner;
        proof_data.to = _to;
        //proof_data.from_registrant = data.registrantData;
        //proof_data.to_registrant = _new_registrant;
        proof_data.timestamp = block.timestamp;
        proof_data.blockNumber = block.number;

        factory.transferDevice(data.owner, _to);
        data.owner = _to;
        //data.registrantData = _new_registrant;
        if (owner != _to) transferOwnership(_to);

        generateTransferProof(proof_data);

        //3rd parameter is a placeholder, emiting two transfers?
       // emit DeviceTransferred(address(this), data.owner, "registrant??");
    }

    function addService(string calldata endpoint, string calldata type_, string calldata description, string calldata fragment) 
    public onlyOp{
        Service memory newService;
        newService.endpoint = endpoint;
        newService.type_ = type_;
        newService.description = description;
        newService.fragment = fragment;
        services.push(newService);
    }
    
    function removeService(string calldata fragment) public onlyOp{
        uint256 length = services.length;
        bytes32 fragmentHash = keccak256(abi.encodePacked(fragment));
        for (uint256 i = 0; i < length; i++) {
            bytes32 currentFragmentHash = keccak256(abi.encodePacked(services[i].fragment));
            if (currentFragmentHash == fragmentHash) {
                services[i] = services[length - 1];
                services.pop();
                break;
            }
        }
    }

    function getDidData() public view returns (DidData memory _didData){
        DidData memory retData;
        retData.contractAddress = address(this);
        retData.controller = data.owner;
        retData.services = services;
        retData.chid = data.chid;
        retData.chainid = block.chainid;
        return retData;
    }

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