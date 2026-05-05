FROM alpine:3.22
RUN apk add --no-cache pgbouncer postgresql-client && \
    addgroup -g 10001 -S pgbouncer && \
    adduser -S -D -H -u 10001 -G pgbouncer pgbouncer
USER pgbouncer
CMD ["pgbouncer", "/etc/pgbouncer/pgbouncer.ini"]
