FROM alpine:3.23

RUN apk add --no-cache pgbouncer postgresql-client gettext && \
    addgroup -g 10001 -S pgbouncer && \
    adduser -S -D -H -u 10001 -G pgbouncer pgbouncer && \
    install -d -o 10001 -g 10001 /var/lib/pgbouncer

COPY pgbouncer.ini /etc/pgbouncer/pgbouncer.ini
COPY userlist.txt.template /etc/pgbouncer/userlist.txt.template
COPY entrypoint.sh /usr/local/bin/pgbouncer-entrypoint.sh
RUN chmod 755 /usr/local/bin/pgbouncer-entrypoint.sh

USER pgbouncer
CMD ["/usr/local/bin/pgbouncer-entrypoint.sh"]
