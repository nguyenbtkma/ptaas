FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y \
    wget \
    openjdk-17-jre \
    unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /zap

RUN wget https://github.com/zaproxy/zaproxy/releases/download/v2.15.0/ZAP_2.15.0_Linux.tar.gz \
    && tar -xzf ZAP_2.15.0_Linux.tar.gz \
    && mv ZAP_2.15.0/* . \
    && rm -rf ZAP_2.15.0*

EXPOSE 8090

CMD ["./zap.sh", "-daemon", "-host", "0.0.0.0", "-port", "8090"]
