# inspired by  https://github.com/Chocobozzz/PeerTube/blob/b9c3a4837e6a5e5d790e55759e3cf2871df4f03c/support/docker/production/Dockerfile.nginx

FROM nginx:alpine

RUN apk add --no-cache openssl \
    && openssl req -x509 -nodes -newkey rsa:2048 -keyout /etc/ssl/private/ssl-cert-snakeoil.key -out /etc/ssl/certs/ssl-cert-snakeoil.pem -days 365 -subj "/CN=localhost"

# remove worker_processes, defined in entrypoint
RUN sed -i 's/worker_processes  auto;//g' /etc/nginx/nginx.conf

COPY ./docker/nginx.entrypoint.sh .
RUN chmod +x nginx.entrypoint.sh

EXPOSE 80 443
ENTRYPOINT []
CMD ["/bin/sh", "nginx.entrypoint.sh"]
