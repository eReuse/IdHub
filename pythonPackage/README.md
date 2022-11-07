# eReuse API 

This package contains various methods to communicate with any ereuse multi-DLT API.

## Installation

You can install the eReuse API package from PyPI. The "requests" library is also necessary.

```sh
pip install --index-url https://test.pypi.org/simple/ ereuseapitest
pip install requests
```

## Usage

Simply import the eReuseAPI as a module in your code. We encourage importing the API class
and the "register_user" method directly.

```sh
from ereuseapi.methods import API, register_user
```

First, register a new user into the desired API. In this example, no ethereum privateKey is given, so the API will automatically
generate one and return it. "register_user" and all the other API methods always return a json object. We will save the "[data].[api_token]"
value of the returned json (it contains the api_token of the registered user, which will be necessary later).

```sh
keyUser1 = methods.register_user("http://endpoint_ip:endpoint_port")['data']['api_token']
```

An example of a json return object for "register_user" method would be:

```json
{
"status": "Success.", 
"data":
    {
    "api_token": "G1tG8mBzmgftK5P.gScPwsXlSoQ94PKkcsHvp6Kiqcq0UguvHus5pytfe5qb9HGANhbWUyvIEZS7ro9y", 
    "eth_pub_key": "0x84fc77d998Ee14AeE099856AcFA51302F165F11a",
    "eth_priv_key": "0xc2d600f7e1bd498fd34a073365c39954bde17c47f936d376c190ff8ff4094030",
    "iota_id": "iota_placeholder"
    }
}
```

Once the user is registered, he is now able to initialize an API object with his token.

```sh
apiUser1 = methods.API("http://endpoint_ip:endpoint_port",keyUser1,"ethereum")
```

From now on, this API object "apiUser1" will be enough to call all the other API methods that require an already registered user.

```sh
apiUser1.register_device("chid")
apiUser1.get_register_proof("chid")
apiUser1.issue_passport("chiddpp" + ":dpp", "docid", "docsig", "issuerid")
```

## API Methods and the API token

Each time a user executes an API call, his complete API token is needed for validation and identification purposes. This is why an "API_token" is needed to initialize an API object.

Each API token has two parts. The "prefix", composed of the first 15 characters, is the public “key” of the API token. The following 64 characters are private and should be known only by its owner.

When user X wants to interact with user Y (target user) through the API, X uses the "prefix" part of the API token of the target user Y.

The following is a list of all the API methods available in the package.

### invalidate_user
Invalidates the user from the API. The user is no longer capable of doing any operation.

```python
invalidate_user()
```
### set_issuer
Gives "Issuer" credential to the target user. A user with an "Issuer" credential can issue new credentials to other users. Only the API Admin can give this credenital.
```python
set_issuer(target_user)
```

### issue_credential
Gives an "Operator", "Verifier" or "Witness" credential to the target user. Only an issuer can issue these credentials.
```python
issue_credential(credential_type, target_user)
```

### register_device
Registers a new device into the DLT. The device CHID must be unique in each DLT.
```python
register_device(deviceCHID)
```


### deRegister_device
Deregister a device from the DLT. New passports or proofs can not be generated in a deregistered device.

```python
deRegister_device(deviceCHID)
```

### issue_passport
Issues a new passport to a device. The device is defined through the mandatory "deviceDPP" argument, which contains the deviceCHID. 
        DeviceDPP format: deviceCHID:xxxx
        Document ID, Document Signature, and Issuer ID are optional.

```python
issue_passport(deviceDPP, docID, docDig, issuerID)
```

### generate_proof
Issues a new proof into a device. DeviceCHID is mandatory.
Document ID, Document Signature, Issuer ID and type are optional.

```python
generate_proof(deviceCHID, docID, docDig, issuerID, proof_type)
```

### transfer_device
 Transfers the ownership of a device to another account.

```python
transfer_device(deviceCHID, newOwner)
```

### get_register_proof
Gets all the registered proofs of a device, ordered by timestamp.
```python
get_register_proof(deviceCHID)
```

### get_issue_proofs
Gets all the passport proofs of a device, ordered by timestamp.
```python
get_issue_proofs(deviceCHID)
```

### get_generic_proofs
Gets all the generic proofs of a device, ordered by timestamp.
```python
get_generic_proofs(deviceCHID)
```


### get_deregister_proofs
Gets all the deregister proofs of a device, ordered by timestamp.
```python
get_deregister_proofs(deviceCHID)
```

### check_user_roles
Gets the current roles of the user.
```python
check_user_roles()
```

### get_did_data
Gets the necessary data to construct the DID document.
```python
get_did_data(deviceCHID)
```

### add_service
Adds a new service to the DID document. Services require an endpoint, a type and a fragment. Description is optional.
```python
add_service(deviceCHID, s_type, endpoint, desc, frag)
```


### remove_service
Removes a service from the DID document. The default service can't be removed.
```python
remove_service(deviceCHID, frag)
```

