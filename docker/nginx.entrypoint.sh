# inspired by https://github.com/Chocobozzz/PeerTube/blob/b9c3a4837e6a5e5d790e55759e3cf2871df4f03c/support/docker/production/entrypoint.nginx.sh

#!/bin/sh
set -e

# Process the nginx template
SOURCE_FILE="/etc/nginx/conf.d/app.template"
TARGET_FILE="/etc/nginx/conf.d/default.conf"
export WEBSERVER_HOST="${APP_WEBSERVER_HOSTNAME}"
export PEERTUBE_HOST="${APP_HOST=}"

envsubst '${WEBSERVER_HOST} ${PEERTUBE_HOST}' < $SOURCE_FILE > $TARGET_FILE

while true; do
  sleep 12h & wait $!;
  nginx -s reload;
done &

nginx -g 'daemon off;'
