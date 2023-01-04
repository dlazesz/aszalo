# From official Debian 11 Bullseye image pinned by its name bullseye-slim
FROM debian:bullseye-slim

# Install noske dependencies
## deb packages
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends \
        python3-pip \
        locales && \
    rm -rf /var/lib/apt/lists/* && \
    sed -i -e 's/# hu_HU.UTF-8 UTF-8/hu_HU.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=hu_HU.UTF-8

ENV LANG hu_HU.UTF-8
ADD . /app/
WORKDIR /app/

RUN pip3 install -r requirements.txt

ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EXPOSE 8000
