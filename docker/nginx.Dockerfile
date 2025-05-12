# inspired by  https://github.com/Chocobozzz/PeerTube/blob/b9c3a4837e6a5e5d790e55759e3cf2871df4f03c/support/docker/production/Dockerfile.nginx

FROM nginx:alpine

COPY ./docker/nginx.entrypoint.sh .
RUN chmod +x nginx.entrypoint.sh

EXPOSE 80 443
ENTRYPOINT []
CMD ["/bin/sh", "nginx.entrypoint.sh"]
