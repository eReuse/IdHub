FROM node:20-alpine3.19

USER root
RUN mkdir -p /home/node/veramoApi/node_modules
WORKDIR /home/node/veramoApi
COPY package*.json ./
COPY tsconfig.json ./


ENV PYTHONUNBUFFERED=1
# src https://stackoverflow.com/questions/62554991/how-do-i-install-python-on-alpine-linux
RUN apk add --update --no-cache python3 jq py3-pip && ln -sf python3 /usr/bin/python
# TODO next version of pyvckit, add pyroaring as dependency and quit it from here
# src https://jairoandres.com/python-dependencies-break-your-system-if-you-want/
RUN pip3 install --no-cache --upgrade pip --break-system-packages setuptools pyvckit pyroaring
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
