FROM kong/kong-gateway:3.5

USER root

# Add custom plugin to the image
COPY kong-plugins/jwt-claims-headers jwt-claims-headers
ENV KONG_PLUGINS=bundled,jwt-claims-headers
RUN cd jwt-claims-headers && luarocks make

USER kong

ENTRYPOINT ["/entrypoint.sh"]
EXPOSE 8000 8443 8001 8444
STOPSIGNAL SIGQUIT
HEALTHCHECK --interval=10s --timeout=10s --retries=10 CMD kong health
CMD ["kong", "docker-start"]
