# DID resolver API
HTTP API that resolves into DID documents the DIDs stored into the verifiable registry.

Format used for the DIDs is:
```
did:ereuse:<CHID>
```

GET requests should be made to:
```
/<DID>
```

## Manual deployment
If not deployed by the main Docker at the [root directory](../):
```javascript
npm i
cd src
node index.js
```
The API is then exposed to port 3011 by default.

### Configuration parameters
Edit the endpoint at line 10 of [resolution.js](src/resolution.js). Point to the Connector HTTP API.