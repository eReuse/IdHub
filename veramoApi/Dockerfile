FROM node:19-alpine3.15

USER root
RUN mkdir -p /home/node/veramoApi/node_modules
WORKDIR /home/node/veramoApi
COPY package*.json ./
COPY tsconfig.json ./


ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 jq && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools pyvckit
RUN apk add --no-cache make
RUN mkdir ~/.npm-global
RUN npm config set prefix '~/.npm-global'
RUN export PATH=~/.npm-global/bin:$PATH
RUN npm install
RUN npm install @veramo/credential-eip712
RUN npm install tsx

COPY src ./src

EXPOSE 3016
WORKDIR /home/node/veramoApi/src
CMD ["./entrypoint.sh"]
