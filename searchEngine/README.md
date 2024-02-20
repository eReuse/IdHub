# DPP search engine
Web app that provides a simple DPP search engine.

## Deployment

### Configuration parameters
Edit [.env](./.env) file:
```javascript
REACT_APP_CONNECTOR_API= // Connector API endpoint
REACT_APP_DPP_INDEXER= // DPP Indexer endpoint
REACT_APP_IOTA_API= // IOTA DPP Registry API endpoint
REACT_APP_IOTA_TOKEN= // IOTA token for the DPP Registry API
REACT_APP_CONNECTOR_API_TOKEN= // Token for the Connector API. Should have a "verifier" credential.
REACT_APP_EREUSE_DID_RESOLVER= // ereuse method DID resolver endpoint.
REACT_APP_ID_INDEX_API= // ID index API endpoint.
REACT_APP_IOTA_EXPLORER= // IOTA Tangle Explorer endpoint
```


### Manual deployment
```javascript
npm i
npm start
```

### Docker deployment
Build and run the Docker image with:
```
docker-compose up
```

