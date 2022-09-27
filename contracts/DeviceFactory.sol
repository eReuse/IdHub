pragma solidity ^0.8.6;

//import "project:/contracts/DepositDevice.sol";
//import "project:/contracts/Ownable.sol";
import "./DepositDevice.sol";
import "./Ownable.sol";
import "./AccessList.sol";

contract DeviceFactory {
    AccessList public roles;

    mapping(address => address[]) deployed_devices;
    mapping(string => address) translation;
    address[] owners;
    address[] devices;

    //-------  EVENTS  -------//
    event DeviceRegistered(address indexed _deviceAddress, uint timestamp);

    constructor(address rolesAddress) {
        roles = AccessList(rolesAddress);
    }

    modifier onlyOp() {
        require(roles.checkIfOperator(msg.sender) == true, "The message sender is not an operator");
        _;
    }

    function registerDevice( 
        string calldata _chid
    ) public onlyOp returns (address _device) {
        require(translation[_chid] == address(0), "Can't register an already registered device");
        DepositDevice newContract = new DepositDevice(
            _chid,
            msg.sender,
            address(this),
            address(roles)
        );
        deployed_devices[msg.sender].push(address(newContract));
        translation[_chid] = address(newContract);
        if(deployed_devices[msg.sender].length == 1) {
            registerOwner(msg.sender);
        }
        devices.push(address(newContract));
        emit DeviceRegistered(address(newContract), block.timestamp);
        return address(newContract);
    }

    function registerOwner(address owner) internal{
        bool owner_exists = false;
        uint256 length = owners.length;
        for (uint256 i = 0; i < length; i++) {
            if(owners[i]==owner){
                owner_exists=true;
                break;
            }
        }
        if(!owner_exists) owners.push(owner);
    }

    //
    function transferDevice(address current_owner, address new_owner) public {
        if(current_owner != new_owner){
            deleteOwnership(current_owner);
            deployed_devices[new_owner].push(msg.sender);
        }
    }

    function deleteOwnership(address owner) internal {
        uint256 length = deployed_devices[owner].length;
        for (uint256 i = 0; i < length; i++) {
            if (deployed_devices[owner][i] == msg.sender) {
                deployed_devices[owner][i] = deployed_devices[owner][length - 1];
                deployed_devices[owner].pop();
                //delete deployed_devices[owner][length - 1];
                //deployed_devices[owner].length--;
                break;
            }
        }
    }

    // function recycle(address _owner) public {
    //     deleteOwnership(_owner);
    // }


    function getDeployedDevices() public view returns (address[] memory _deployed_devices){
        return deployed_devices[msg.sender];
    }


    function getAllDeployedDevices() public view returns (address[] memory _devices){
        return devices;
    }

    function getAddressFromChid(string calldata _chid) public view returns (address _address){
        return translation[_chid];
    }
}