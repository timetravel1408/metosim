FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy landing page
COPY index.html /usr/share/nginx/html/index.html

EXPOSE 8080

# Railway uses PORT env var — override nginx listen port at runtime
CMD sh -c "sed -i 's/listen 8080/listen ${PORT:-8080}/' /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"
