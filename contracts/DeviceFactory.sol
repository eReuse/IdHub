pragma solidity ^0.4.25;

//import "project:/contracts/DepositDevice.sol";
//import "project:/contracts/Ownable.sol";
import "./DepositDevice.sol";
import "./Ownable.sol";

contract DeviceFactory {
    mapping(address => address[]) deployed_devices;
    mapping(string => address) translation;
    address[] owners;
    address[] devices;

    //-------  EVENTS  -------//
    event DeviceRegistered(address indexed _deviceAddress, uint timestamp);


    function registerDevice( 
        string _chid
    ) public returns (address _device) {
        require(translation[_chid] == address(0), "Can't register an already registered device");
        DepositDevice newContract = new DepositDevice(
            _chid,
            msg.sender,
            address(this)
        );
        deployed_devices[msg.sender].push(newContract);
        translation[_chid] = newContract;
        if(deployed_devices[msg.sender].length == 1) {
            registerOwner(msg.sender);
        }
        devices.push(newContract);
        emit DeviceRegistered(newContract, block.timestamp);
        return newContract;
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

    // function transfer(address current_owner, address new_owner) public {
    //     if(current_owner != new_owner){
    //         deleteOwnership(current_owner);
    //         deployed_devices[new_owner].push(msg.sender);
    //     }
    // }

    function deleteOwnership(address owner) internal {
        uint256 length = deployed_devices[owner].length;
        for (uint256 i = 0; i < length; i++) {
            if (deployed_devices[owner][i] == msg.sender) {
                deployed_devices[owner][i] = deployed_devices[owner][length - 1];
                delete deployed_devices[owner][length - 1];
                deployed_devices[owner].length--;
                break;
            }
        }
    }

    // function recycle(address _owner) public {
    //     deleteOwnership(_owner);
    // }


    function getDeployedDevices() public view returns (address[] _deployed_devices){
        return deployed_devices[msg.sender];
    }


    function getAllDeployedDevices() public view returns (address[] _devices){
        return devices;
    }

    function getAddressFromChid(string _chid) public view returns (address _address){
        return translation[_chid];
    }
}