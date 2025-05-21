# inspired by https://github.com/Chocobozzz/PeerTube/blob/b9c3a4837e6a5e5d790e55759e3cf2871df4f03c/support/docker/production/entrypoint.nginx.sh

#!/bin/sh
set -e
set -u
# DEBUG
set -x

# Process the nginx template
SOURCE_FILE="/etc/nginx/conf.d/app.template"
TARGET_FILE="/etc/nginx/conf.d/default.conf"
export WEBSERVER_HOST="${WEBSERVER_HOST}"
export APP_HOST="${APP_HOST}"

if [ "${FAKE_HTTP_CERT:-true}" = "true" ]; then
  # do same snakeoil certs as `ssl-cert` debian package
  export SSL_CERTIFICATE_PATH="/etc/ssl/certs/ssl-cert-snakeoil.pem";
  export SSL_CERTIFICATE_KEY_PATH="/etc/ssl/private/ssl-cert-snakeoil.key";
else
  export SSL_CERTIFICATE_PATH="/etc/letsencrypt/live/${WEBSERVER_HOST}/fullchain.pem"
  export SSL_CERTIFICATE_KEY_PATH="/etc/letsencrypt/live/${WEBSERVER_HOST}/privkey.pem";
fi

envsubst '${WEBSERVER_HOST} ${APP_HOST} ${SSL_CERTIFICATE_PATH} ${SSL_CERTIFICATE_KEY_PATH}' < $SOURCE_FILE > $TARGET_FILE

# DEBUG
#sleep infinity

while [ ! "${FAKE_HTTP_CERT:-}" = "true" ]; do
  sleep 12h & wait $!;
  nginx -s reload;
done &

exec nginx -g 'worker_processes 2; daemon off;'
