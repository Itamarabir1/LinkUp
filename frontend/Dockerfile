# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG SENTRY_AUTH_TOKEN
ARG SENTRY_ORG
ARG SENTRY_PROJECT
RUN npm run build

# Production stage — non-root nginx (listens on 8080)
FROM nginxinc/nginx-unprivileged:alpine
USER root
RUN apk add --no-cache gettext
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/config.template.js /etc/linkup/config.template.js
COPY docker/firebase-messaging-sw.template.js /etc/linkup/firebase-messaging-sw.template.js
COPY docker/40-render-config.sh /docker-entrypoint.d/40-render-config.sh
RUN chmod +x /docker-entrypoint.d/40-render-config.sh \
    && chown -R nginx:nginx /usr/share/nginx/html /etc/linkup
USER nginx
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
