FROM ubuntu:latest
RUN apt-get update && apt-get upgrade -y && apt-get install -y nginx
COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html /var/www/index.html
COPY index.js /var/www/index.js
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]