FROM node:19-alpine3.15

RUN mkdir -p /home/node/observerModule/node_modules && chown -R node:node /home/node/observerModule
WORKDIR /home/node/observerModule
COPY --chown=node:node package*.json ./

USER root
RUN npm install

EXPOSE 3014
WORKDIR /home/node/observerModule/src
CMD ["node", "./index.js"]