# DPP indexer
While running, indexes DPP info by listening to chain events and asking inventory services for extra data. Also exposes an HTTP API to provide search functionality.

Searches should be done by GET to:
```
/search?query=<search query>
```

## Deployment
### Configuration parameters
Edit [.env](src/.env) file.
- NODE_IP should point to a node of the chain (rpc endpoint).
- ID_INDEX should point to a [ID index API](../idIndexApi) instance.

### Manual deployment
```javascript
npm i
cd src
node index.js
```

### Docker deployment
Build and run the Docker image with:
```
docker-compose up
```
The API is then exposed to port 3013 by default.

