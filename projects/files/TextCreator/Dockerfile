# Dockerfile
FROM nginx:1.27-alpine

# Remove default site
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy our custom nginx config
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Copy static site (match the paths in index.html)
COPY site/ /usr/share/nginx/html/

# Optional: set immutable, gzip-able static caching
RUN apk add --no-cache bash
