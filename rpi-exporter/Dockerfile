FROM balenalib/raspberry-pi:latest

RUN apt-get update
RUN apt-get install -y python3 python3-pip

RUN pip3 install prometheus_client schedule

COPY rpi-stats.py /

# for text
# text file export to /host/rpi-exporter. set mount target host directory by volume like this.
# ex: -v "/var/lib/prometheus/node-exporter:/host/rpi-exporter"
ENTRYPOINT ["python3", "/rpi-stats.py", "100", "10", "text"]

# for gataway
#ENTRYPOINT ["python3", "/rpi-stats.py", "100", "10", "gateway", "192.168.10.5:9091"]