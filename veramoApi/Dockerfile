FROM node:19-alpine3.15

RUN mkdir -p /home/node/veramoApi/node_modules && chown -R node:node /home/node/veramoApi
WORKDIR /home/node/veramoApi
COPY --chown=node:node package*.json ./
COPY --chown=node:node tsconfig.json ./

USER root
RUN npm install
RUN node 

EXPOSE 3016
WORKDIR /home/node/veramoApi/src
CMD ["node", "./index.js"]