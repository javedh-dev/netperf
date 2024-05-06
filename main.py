#!/usr/bin/env python3

from influxdb_client.client.write_api import SYNCHRONOUS
from schema import Schema, And, Use, SchemaError
import iperf3
import influxdb_client
import time
import yaml
import logging
import os
import speedtest


schema = Schema(
        {
            'influx': {
                'url': And(str, len),
                'token': And(str, len),
                'org': And(str, len),
                'bucket': And(str, len)
            },
            'iperf': {
                'name': And(str,len),
                'interval': And(Use(int), lambda n: 30<=n<=60),
                'servers': [
                    {
                        'name': And(str, len),
                        'address': And(str,len),
                        'port': And(Use(int), lambda n: 1025<= n <=65535),
                        'duration': And(Use(int), lambda n: 0< n <=60)
                    }
                ]
            }
        }
    )


def get_config():
    with open("config.yaml", "r") as file:
        config_text = file.read()
        config_text = os.path.expandvars(config_text)
        config = yaml.safe_load(config_text)
        file.close()
    schema.validate(config)
    return config

def initialize_influx():
    try:
        influx_config = config["influx"]
        influx_client = influxdb_client.InfluxDBClient(
            url=influx_config["url"], token=influx_config["token"], org=influx_config["org"]
        )
        if influx_client.ready().status!='ready':
            raise Exception("Couldn't connect to influx DB")
        return influx_client.write_api(write_options=SYNCHRONOUS)
    except Exception as e:
        raise Exception("Failed to initialize the influx DB", e)


def write_to_db(record):
    influx_config = config["influx"]
    influx_write_api.write(
        bucket=influx_config["bucket"], org=influx_config["org"], record=record
    )


def gather_stats():
    for server in config["iperf"]["servers"]:
        try:
            client = iperf3.Client()
            client.server_hostname = server["address"]
            client.port = server["port"]
            client.duration = server["duration"]
            result = client.run()
            del client

            logger.debug("Pushing data for server '%s'", server["name"])
            record = (
                influxdb_client.Point("bandwidth")
                .tag("source", config["iperf"]["name"])
                .tag("destination", server["name"])
                .field("upload", result.sent_Mbps)
                .field("download", result.received_Mbps)
            )
            write_to_db(record)
        except Exception:
            logger.error("Failed to process stats for %s", server['name'])

def setup_logging():
    global logger 
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    file_handler = logging.FileHandler('netperf.log')
    stream_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

def check_env():
    if (os.environ.get("HOST_NAME") and os.environ.get("INFLUX_TOKEN")):
        return True
    else:
        raise Exception("INFLUX_TOEKN or HOST_NAME environment variables not exists")

def calculate_speed():
    st = speedtest.Speedtest(secure=True)
    logger.debug("Pushing data for server Internet Speed")
    record = (
        influxdb_client.Point("speedtest")
        .tag("source", config["iperf"]["name"])
        .field("download", st.download())
        .field("upload", st.upload())
        .field("ping", st.results.ping)
    )
    write_to_db(record)
        

def configure():
    global config 
    global influx_write_api
    try:
        setup_logging()
        logger.info("Configuring the netperf...")
        check_env()
        config = get_config()
        influx_write_api = initialize_influx()
    except FileNotFoundError as e:
        logger.exception("Please ensure that config.yaml file is present.")
        raise e
    except SchemaError as e:
        logger.exception("Validation failed : Please validate the schema for config.yaml file")
        raise e
    except Exception as e:
        logger.exception("Runtime Error Occurred : ")
        raise e

def start():
    logger.info("Starting the netperf stats collector...")
    sleep_time = int(config['iperf']['interval']) - sum(map(lambda n: int(n['duration']),config['iperf']['servers']))
    while True:
        logger.debug("-"*50)
        gather_stats()
        calculate_speed()
        logger.debug("-"*50)
        logger.debug("Sleeping for %ss.", sleep_time)
        time.sleep(sleep_time if sleep_time>=0 else 0)

if __name__ == "__main__":
    configure()
    start()