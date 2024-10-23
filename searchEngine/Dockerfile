FROM node:19-alpine3.15

RUN mkdir -p /home/node/searchEngine/node_modules && chown -R node:node /home/node/searchEngine
WORKDIR /home/node/searchEngine
COPY --chown=node:node package*.json ./

USER root
RUN npm install

EXPOSE 3000
WORKDIR /home/node/searchEngine

COPY entrypoint.sh .
CMD ["./entrypoint.sh"]
