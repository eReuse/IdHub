FROM node:20.10.0-alpine

RUN mkdir -p /home/node/didResolverAPI/node_modules && chown -R node:node /home/node/didResolverAPI && mkdir -p /home/node/didResolverModule/node_modules && chown -R node:node /home/node/didResolverModule
WORKDIR /home/node/didResolverAPI
COPY --chown=node:node didResolverApi/package*.json ./

WORKDIR /home/node/didResolverModule
COPY --chown=node:node didResolverModule/package*.json ./
WORKDIR /home/node/didResolverAPI
USER node
RUN npm install

WORKDIR /home/node/didResolverModule
RUN npm install

EXPOSE 3011
WORKDIR /home/node/didResolverAPI/src
# COPY ../.env ./
CMD ["node", "./index.js"]