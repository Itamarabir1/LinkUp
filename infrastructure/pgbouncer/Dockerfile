FROM alpine:3.22
RUN apk add --no-cache pgbouncer postgresql-client && \
    adduser -S -D -H pgbouncer
USER pgbouncer
CMD ["pgbouncer", "/etc/pgbouncer/pgbouncer.ini"]
