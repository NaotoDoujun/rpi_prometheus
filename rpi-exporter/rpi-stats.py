#!/usr/bin/env python3
#coding:utf-8$

import os
import sys
import schedule
import time
import socket
from subprocess import getoutput
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway, write_to_textfile

argslen = len(sys.argv)
NODENAME = sys.argv[1] if argslen > 1 else "100" # device node name
INTERVAL = int(sys.argv[2]) if argslen > 2 else 10 # schedule interval(sec)
EXPORT_TYPE = sys.argv[3] if argslen > 3 else "text" # export type(text or gateway)
TEXTFILE_DIR = "/host/rpi-exporter"
if EXPORT_TYPE == "text":
    METRICS_FILE = TEXTFILE_DIR + "/raspi-metrics.prom"
elif EXPORT_TYPE == "gateway":
    GATEWAY_URL = sys.argv[4] if argslen > 4 else "192.168.10.5:9091" # pushgateway url 

def connectable(ip, port):
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    location = (ip, port)
    result_of_check = a_socket.connect_ex(location)
    a_socket.close()
    if result_of_check == 0:
        return True
    else:
        return False

def export():
    registry = CollectorRegistry()
    temp_g = Gauge('rpi_temperature', 'Temperatures of the components in degree celsius.', ['node','sensor','type'], registry=registry)
    freq_g = Gauge('rpi_frequency', 'Clock frequencies of the components in hertz.', ['node','component'], registry=registry)    
    volt_g = Gauge('rpi_voltage', 'Voltages of the components in volts.', ['node','component'], registry=registry)
    mem_g = Gauge('rpi_memory', 'Memory split of CPU and GPU in bytes.', ['node','component'], registry=registry)
    thro_g = Gauge('rpi_throttled', 'Throttled state of the system.', ['node','component'], registry=registry)

    # Get temperatures
    for folder,subfolders,files in os.walk("/sys/class/thermal/"):
        for sensor_name in subfolders:
            temp_celsius = getoutput("awk '{printf \"%.3f\", $1/1000}' /sys/class/thermal/" + sensor_name + "/temp")
            sensor_type = getoutput("cat /sys/class/thermal/" + sensor_name + "/type")
            temp_g.labels(NODENAME, sensor_name, sensor_type).set(temp_celsius)

    # Get component frequencies
    for freq_component in ['arm','core','h264','isp','v3d','uart','pwm','emmc','pixel','vec','hdmi','dpi']:
        freq = getoutput("vcgencmd measure_clock " + freq_component).split('=')
        freq_g.labels(NODENAME, freq_component).set(freq[1])

    # Get component voltages
    for volt_component in ['core', 'sdram_c', 'sdram_i', 'sdram_p']:
        volt = getoutput("vcgencmd measure_volts " + volt_component).split('=')
        volt_g.labels(NODENAME, volt_component).set(volt[1].replace("V", ""))

    # Get memory split of CPU vs GPU
    for mem_component in ['arm', 'gpu']:
        mem = getoutput("vcgencmd get_mem " + mem_component).split('=')
        memory = int(mem[1].replace("M", ""))
        mem_g.labels(NODENAME, mem_component).set(memory * 1024 * 1024)

    # Get throttled events
    thro = getoutput("vcgencmd get_throttled")
    throttled = int(thro.strip().split("=")[1], 16)
    under_voltage_detected = 1 if throttled & 1 << 0 else 0
    arm_frequency_capped = 1 if throttled & 1 << 1 else 0
    currently_throttled = 1 if throttled & 1 << 2 else 0
    soft_temperature = 1 if throttled & 1 << 3 else 0
    thro_g.labels(NODENAME, 'under_voltage_detected').set(under_voltage_detected)
    thro_g.labels(NODENAME, 'arm_frequency_capped').set(arm_frequency_capped)
    thro_g.labels(NODENAME, 'currently_throttled').set(currently_throttled)
    thro_g.labels(NODENAME, 'soft_temperature').set(soft_temperature)

    if EXPORT_TYPE == "text":
        # Write to textfile
        if os.access(TEXTFILE_DIR, os.W_OK): write_to_textfile(METRICS_FILE, registry=registry)
    elif EXPORT_TYPE == "gateway":
        url = GATEWAY_URL.split(':')
        if(len(url) > 1 and connectable(url[0], int(url[1]))):
            # Push to gateway
            push_to_gateway(GATEWAY_URL, job='rpi-exporter', registry=registry)


if __name__ == '__main__':

    # Schedule
    schedule.every(INTERVAL).seconds.do(export)

    while True:
        schedule.run_pending()
        time.sleep(1)