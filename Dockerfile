FROM nginx:alpine
COPY index.html schedule.js uitleg.html /usr/share/nginx/html/
COPY privacy.html footer.css theme.js theme.css /usr/share/nginx/html/
COPY assets/ /usr/share/nginx/html/assets/
