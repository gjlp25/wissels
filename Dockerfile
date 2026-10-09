FROM nginx:alpine
COPY index.html schedule.js uitleg.html /usr/share/nginx/html/
COPY assets/ /usr/share/nginx/html/assets/
