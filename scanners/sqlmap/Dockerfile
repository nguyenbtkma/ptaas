FROM python:3.11-slim

RUN apt update && apt install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git /sqlmap

WORKDIR /sqlmap

ENTRYPOINT ["sleep", "infinity"]
