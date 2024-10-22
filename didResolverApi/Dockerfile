FROM node:20.10.0-alpine

RUN mkdir -p /home/node/didResolverApi/node_modules && chown -R node:node /home/node/didResolverApi && mkdir -p /home/node/didResolverModule/node_modules && chown -R node:node /home/node/didResolverModule
WORKDIR /home/node/didResolverApi
COPY --chown=node:node didResolverApi/package*.json ./

WORKDIR /home/node/didResolverModule
COPY --chown=node:node didResolverModule/package*.json ./
WORKDIR /home/node/didResolverApi
USER node
RUN npm install

WORKDIR /home/node/didResolverModule
RUN npm install
COPY didResolverModule/src /home/node/didResolverModule/src

EXPOSE 3011
WORKDIR /home/node/didResolverApi/src
COPY didResolverApi/src /home/node/didResolverApi/src
# COPY ../.env ./
CMD ["node", "./index.js"]
