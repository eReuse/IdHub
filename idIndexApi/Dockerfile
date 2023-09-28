FROM node:19-alpine3.15

RUN mkdir -p /home/node/idIndexApi/node_modules && chown -R node:node /home/node/idIndexApi
WORKDIR /home/node/idIndexApi
COPY --chown=node:node package*.json ./

USER root
RUN npm install

EXPOSE 3012
WORKDIR /home/node/idIndexApi/src
CMD ["node", "./index.js"]