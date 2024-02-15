# Prototype search engine
This service allows for lookup of a particular DPP by inputting a CHID or CHID:PHID.

## Installation
Edit lines 11 and 22 of [dpp.py](dpp.py) with URLs for the "ID Index API" and "DID Resolver API" respectively. 

Build and run the Docker image with:
```
docker-compose up
```

The web service is then deployed to port 80 by default.