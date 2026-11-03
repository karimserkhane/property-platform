FROM ghcr.io/valhalla/valhalla-scripted@sha256:e2078b638205fba6ef246d8ae731d7f197b346a0ebc74fb5f41b01db50504c90
RUN mkdir -p /routing && chown 1000:1000 /routing
COPY infra/local/routing/server.py /opt/platform/routing-server.py
USER 1000:1000
ENTRYPOINT ["python3", "/opt/platform/routing-server.py"]
