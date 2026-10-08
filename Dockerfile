FROM nginx:alpine
COPY index.html schedule.js /usr/share/nginx/html/
