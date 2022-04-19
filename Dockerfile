FROM node:15.14.0-alpine

RUN mkdir -p /home/node/app/node_modules && chown -R node:node /home/node/app
WORKDIR /home/node/app
COPY --chown=node:node package*.json ./
USER node
RUN npm install express -save && npm install ethers --save && npm install crypto-js --save && npm install generate-api-key --save && npm install node-persist --save && npm install body-parser --save && npm install @iota/is-client --save && npm install fs --save
COPY --chown=node:node src ./src

EXPOSE 3010
CMD ["node", "./src/routes/devices.js"]
