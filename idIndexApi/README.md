# ID Index API
This HTTP API is to be used by inventory services to request an ID. This ID is then mapped to any desired URL, enabling name translation when writing the ID to the verifiable registry.

Current endpoints are:
- /getURL: to get the URL assigned to an ID.
- /getAll: to get the whole index.
- /registerURL: to register a URL to a new ID.

## Installation
Build and run the Docker image with:
```
docker-compose up
```

The API is then exposed to port 3012 by default.