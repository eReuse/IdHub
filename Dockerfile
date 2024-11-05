FROM node:20.10.0-alpine
RUN mkdir -p /home/node/app/node_modules && chown -R node:node /home/node/app
WORKDIR /home/node/app
USER node
COPY --chown=node:node package*.json ./
RUN npm install express ethers crypto-js node-persist body-parser fs cors hardhat '@nomicfoundation/hardhat-ethers' --save
COPY --chown=node:node contracts ./contracts
COPY --chown=node:node scripts ./scripts
COPY --chown=node:node src ./src
COPY --chown=node:node hardhat.config.js ./hardhat.config.js
RUN npx hardhat vars set TEST_NODE_IP blockchain_test_node
RUN mkdir -p /home/node/app/shared && chown -R node:node /home/node/app/shared

EXPOSE 3010
# WORKDIR /home/node/app/src/
# COPY ./.env ./
CMD ["./src/entry_point.sh"]
