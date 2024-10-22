FROM node:20.10.0-alpine
RUN mkdir -p /home/node/app/node_modules && chown -R node:node /home/node/app
WORKDIR /home/node/app/

USER node
RUN npm init -y
RUN npm install axios --save

COPY entrypoint.sh .
COPY scripts scripts
CMD ["./entrypoint.sh"]
