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