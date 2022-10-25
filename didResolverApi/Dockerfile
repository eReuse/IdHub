FROM node:19-alpine3.15

RUN mkdir -p /home/node/didResolverAPI/node_modules && chown -R node:node /home/node/didResolverAPI
WORKDIR /home/node/didResolverAPI
COPY --chown=node:node package*.json ./
USER node
RUN npm install

EXPOSE 3011
WORKDIR /home/node/didResolverAPI/src
CMD ["node", "./index.js"]