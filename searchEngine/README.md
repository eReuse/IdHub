# DPP search engine
Web app that provides a simple DPP search engine.

## Deployment

### Configuration parameters
Edit source files:
- [Dpp.js](src/Dpp.js)
```
Line 13: endpoint of the connector API
Line 14: token of a connector API user. Should have Verifier credential.
```
- [SearchResultsPage.js](src/SearchResultsPage.js)
```
Line 13: endpoint of the DPP indexer
```
- [SearchResultsPageDeep.js](src/SearchResultsPageDeep.js)
```
Line 12: endpoint of the DID resolver
Line 13: endpoint of the ID index API
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

