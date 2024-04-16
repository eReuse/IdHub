FROM node:20.10.0-alpine

RUN mkdir -p /home/node/observerModule/node_modules && chown -R node:node /home/node/observerModule
WORKDIR /home/node/observerModule
COPY --chown=node:node observerModule/package*.json ./

USER root
RUN npm install

EXPOSE 3014
WORKDIR /home/node/observerModule/src
# COPY ./.env ./
CMD ["./entry_point.sh"]