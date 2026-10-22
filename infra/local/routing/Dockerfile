FROM ghcr.io/valhalla/valhalla-scripted@sha256:eaad372b8ef31e3e4592c442875aeb1375fbf5aeaa0d259b469e3b46583ab10d
RUN mkdir -p /routing && chown 1000:1000 /routing
COPY infra/local/routing/server.py /opt/platform/routing-server.py
USER 1000:1000
ENTRYPOINT ["python3", "/opt/platform/routing-server.py"]
