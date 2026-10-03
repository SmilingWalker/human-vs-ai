FROM python:3.11-slim

WORKDIR /workspace
COPY workspace/ /workspace/

# skills injection point (managed by evalscope skillsbench runner;
# stripped automatically in no-skill mode)
COPY skills/ /skills/
