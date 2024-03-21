FROM node:16.13.0-alpine

RUN mkdir -p /home/node/app/node_modules && chown -R node:node /home/node/app
WORKDIR /home/node/app
COPY --chown=node:node package*.json ./
COPY --chown=node:node contracts ./contracts
COPY --chown=node:node migrations ./migrations
COPY --chown=node:node truffle-config.js ./truffle-config.js

USER node
RUN npm install truffle@5.4.21 @truffle/hdwallet-provider@1.5.1 express ethers crypto-js node-persist body-parser @iota/is-client fs cors --save --loglevel=error
RUN ./node_modules/.bin/truffle migrate --network abc2_besu --reset
COPY --chown=node:node src ./src

USER root
EXPOSE 3010
WORKDIR /home/node/app/src/
CMD ["node", "./index.js"]
