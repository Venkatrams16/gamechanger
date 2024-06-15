FROM python:3.10.8-slim-buster

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt

RUN pip3 install -U pip && \
    pip3 install -U -r /requirements.txt

RUN mkdir /gamechanger
WORKDIR /gamechanger

COPY start.sh /gamechanger/start.sh
RUN chmod +x /gamechanger/start.sh

CMD ["/bin/bash", "/gamechanger/start.sh"]
