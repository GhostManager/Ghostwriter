FROM postgres:16.4

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance

RUN find /usr/local/bin/maintenance/ -type f -exec sed -i "s/$(printf '\r')\$//" '{}' ';' \
    && chmod +x /usr/local/bin/maintenance/* \
    && mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance
