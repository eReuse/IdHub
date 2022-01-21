pragma solidity ^0.4.25;

contract DeviceFactoryInterface {
    mapping(address => address[]) deployed_devices;
    mapping(string => address) translation;
    address[] owners;
    address[] devices;

    //function transfer(address current_owner, address _new_owner) public;
    function registerDevice(string _chid)public returns (address _device);
    function registerOwner(address owner) internal;
    function deleteOwnership(address owner) internal;
    //function recycle(address _owner) public;
    function getDeployedDevices() public view returns (address[] _deployed_devices);
    function getAllDeployedDevices() public view returns (address[] _address);
    function getAddressFromChid(string _chid) public view returns (address _address);
}
