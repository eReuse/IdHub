// SPDX-License-Identifier: MIT

pragma solidity >=0.4.16 <0.9.0;

struct AttributeValue {
    uint256 attributeId;
    string value;
}

// Attribute registration
struct Attribute {
    string attributeURI;
    uint256 attributeId;
}


interface IAbacContract {
    event NewAttribute(string attributeURI, uint attributeId);

    event DidReady(string did);

    event AttributesReady(AttributeValue[] attrValues);

    /**
     *.  Returns the attribute Id of an attribute URI as registered on the Smart Contract.
     */
    function getAttributeId(string calldata attributeURI)
        external
        view
        returns (uint256);

    /**
     *.  Lists the attribute URIs registered
     */
    function listAttributeURIs() external view returns (string[] memory);

    /**
     *. Lists the attributes known by the Smart Contract
     */
    function listAttributes()
        external
        view
        returns (uint256[] memory, string[] memory);

    /**
     *  Retrieves the account by DID
    */
    function getAccount(string calldata did)
        external
        view
        returns (address);

    /**
     *.  Retrieves the DID by account
     */
    function getDid(address addr) external returns (string memory);

    function getAccountAttributes(address addr)
        external
        returns (AttributeValue[] memory);

    /**
     *.  Returns false if the account attribute is known, set on the account, and is no longer valid. 
     *.  Returns true in all other situations. If attribute not known reverts. 
     */
    function isAccountAttributeValid(uint attributeId, address account) external view returns (bool);
}