FROM alpine:3.23
RUN apk add --no-cache pgbouncer postgresql-client && \
    addgroup -g 10001 -S pgbouncer && \
    adduser -S -D -H -u 10001 -G pgbouncer pgbouncer
USER pgbouncer
CMD ["pgbouncer", "/etc/pgbouncer/pgbouncer.ini"]
