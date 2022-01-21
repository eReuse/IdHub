FROM node:15.14.0-alpine

RUN mkdir -p /home/node/app/node_modules && chown -R node:node /home/node/app
WORKDIR /home/node/app
COPY --chown=node:node package*.json ./
USER node
RUN npm install express -save && npm install ethers --save && npm install sha3 --save
COPY --chown=node:node src ./src

EXPOSE 3005
CMD ["node", "./src/routes/devices.js"]
