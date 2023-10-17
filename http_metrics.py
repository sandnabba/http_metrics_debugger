import pycurl
import io
import sys
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import argparse
import time
import yaml
import socket

def load_config(file_path):
    try:
        with open(file_path, 'r') as config_file:
            return yaml.safe_load(config_file)
    except FileNotFoundError:
        print(f"Configuration file {file_path} not found.")
        sys.exit(1)

def send_to_influxdb(url, metrics, influx_config):
    # Use the InfluxDB configuration from the configuration file
    client = InfluxDBClient(
        url=influx_config.get("url"),
        token=influx_config.get("token"),
        org=influx_config.get("org")
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)

    # Create a data point with the URL as a tag and the location as a tag
    point = Point("http_metric_timings") \
        .tag("url", url) \
        .tag("location", influx_config.get("location")) \
        .field("dns_resolution_time", metrics["dns_resolution_time"]) \
        .field("connection_time", metrics["connection_time"]) \
        .field("appconnect_time", metrics["appconnect_time"]) \
        .field("pretransfer_time", metrics["pretransfer_time"]) \
        .field("ttfb_time", metrics["ttfb_time"]) \
        .field("total_request_time", metrics["total_request_time"]) \
        .tag("response_code", metrics["response_code"]) \
        .time(datetime.utcnow())

    # Write the data point to InfluxDB
    write_api.write(influx_config.get("bucket"), influx_config.get("org"), point)

def perform_http_request(url, method, curl, post_data=None):
    # Reuse pycurl object if passed
    if curl is None:
        c = pycurl.Curl()
    else:
        c = curl

    # Create a buffer to capture response data
    response_buffer = io.BytesIO()

    # Set the URL and other curl options
    c.setopt(pycurl.URL, url)
    c.setopt(pycurl.WRITEFUNCTION, response_buffer.write)
    c.setopt(pycurl.CUSTOMREQUEST, method)

    if method == "POST" and post_data is not None:
        c.setopt(pycurl.POSTFIELDS, post_data)

    # Enable the necessary timer options
    c.setopt(pycurl.NOPROGRESS, 0)
    c.setopt(pycurl.XFERINFOFUNCTION, lambda dltotal, dlnow, ultotal, ulnow: None)

    # Perform the request
    c.perform()

    # Get timing information
    dns_resolution_time = c.getinfo(pycurl.NAMELOOKUP_TIME)
    connection_time = c.getinfo(pycurl.CONNECT_TIME)
    appconnect_time = c.getinfo(pycurl.APPCONNECT_TIME)
    pretransfer_time = c.getinfo(pycurl.PRETRANSFER_TIME)
    ttfb_time = c.getinfo(pycurl.STARTTRANSFER_TIME)
    total_request_time = c.getinfo(pycurl.TOTAL_TIME)

    # Get other relevant information
    data_received = c.getinfo(pycurl.SIZE_DOWNLOAD)
    response_code = c.getinfo(pycurl.RESPONSE_CODE)

    if curl is None:
        # Clean up the pycurl.Curl object
        c.close()

    # Debug: Print the response body.
    # Could be moved to some argument in the future.
    #response_body = response_buffer.getvalue()
    #print(response_body)

    return {
        "dns_resolution_time": dns_resolution_time,
        "connection_time": connection_time,
        "appconnect_time": appconnect_time,
        "pretransfer_time": pretransfer_time,
        "ttfb_time": ttfb_time,
        "total_request_time": total_request_time,
        "data_received_kb": data_received / 1024,
        "response_code": response_code
    }

def print_metrics(metrics, loop_count=None):
    # Print statistics if more than a single run:
    if loop_count is not None:
        print(f"Iteration {loop_count}:")
        print("---------------------------------")

    # Print the metrics including content download time
    print(f"DNS Resolution Time: {metrics['dns_resolution_time']:.2f} seconds")
    print(f"Connection Time: {metrics['connection_time']:.2f} seconds")
    print(f"AppConnect Time: {metrics['appconnect_time']:.2f} seconds")
    print(f"Pre-transfer Time: {metrics['pretransfer_time']:.2f} seconds")
    print(f"Time to First Byte (TTFB): {metrics['ttfb_time']:.2f} seconds")
    print("")
    print(f"Total Request Time: {metrics['total_request_time']:.2f} seconds")
    print(f"Total Data Received: {metrics['data_received_kb']:.2f} KB")
    print(f"HTTP Response Code: {metrics['response_code']}")

    print("---------------------------------\n")

def main():
    parser = argparse.ArgumentParser(description="HTTP endpoint testing and metrics collection")
    parser.add_argument("-c", "--config", type=str, default=None, help="Path to a configuration file")
    if not ("-c" or "--config") in sys.argv:
        parser.add_argument("url", help="The URL to test")
        parser.add_argument("-x", "--method", type=str, default="GET", help="HTTP method to use, e.g.GET, POST. (Default: GET)")
        parser.add_argument("-i", "--interval", type=int, default=10, help="Interval between tests in seconds (default: 10s)")
        parser.add_argument("-l", "--loop", type=int, default=None, help="Number of times to run (default: 1 time)")
        parser.add_argument("-r", "--reuse-connection", action="store_true", default=False, help="Reuse the same HTTP connection")
        parser.add_argument("--influx", action="store_true", default=False, help="Send metrics to InfluxDB")
        parser.add_argument("-d", "--data", type=str, default=None, help="Data to include in the request body (for POST requests)")
        parser.add_argument("-b", "--background", action="store_true", default=False, help="Run forever as a background service")

    args = parser.parse_args()
    config_file = args.config

    if config_file:
        config = load_config(config_file)
        url = config.get("url")
        method = config.get("method", "GET")
        interval = config.get("interval", 0)
        loop_count = config.get("loop", 1)
        background = config.get("background", False)
        reuse_connection = config.get("reuse_connection", False)
        post_data = config.get("data")
        send_to_influx = config.get("influx", {}).get("enabled", False)
        influx_config = config.get("influx", {})  # Extract the entire InfluxDB config
    else:
        # Set default values
        url = args.url
        method = args.method
        interval = args.interval
        loop_count = args.loop
        reuse_connection = args.reuse_connection
        send_to_influx = args.influx
        background = args.background
        influx_url = "http://your_influxdb_host:8086"  # Provide default values here
        influx_token = "your_influxdb_token"
        influx_org = "your_influxdb_org"
        influx_bucket = "your_influxdb_bucket"
        
        # Get the machine's hostname and set it as the default "location" if not specified
        influx_location = socket.gethostname()  
        post_data = args.data

    start_time = time.time()

    if reuse_connection:
        print("Reusing connections!")
        curl = pycurl.Curl()
    else:
        curl = None

    if loop_count is not None and not background:
    # Run a fixed number of requests and print statistics.
        total_time = 0
        metrics_sum = {
            "dns_resolution_time": 0,
            "connection_time": 0,
            "appconnect_time": 0,
            "pretransfer_time": 0,
            "ttfb_time": 0,
            "total_request_time": 0,
            "data_received_kb": 0,
            "response_code": 0
        }

        try:
            for r in range(loop_count):
                metrics = perform_http_request(url, method, curl, post_data)
                print_metrics(metrics, loop_count=r)
                if send_to_influx:
                    send_to_influxdb(url, metrics, influx_config)
                time.sleep(interval)

                # Accumulate metrics for averaging
                for key in metrics_sum:
                    metrics_sum[key] += metrics[key]
                total_time += metrics["total_request_time"]

            # Calculate the average metrics:
            average_metrics = {
                key: metrics_sum[key] / loop_count for key in metrics_sum
            }

            # Calculate time between requests:
            sleep_time = loop_count * interval

            # Print summary:
            print("=================================")
            print("Average Metrics:")
            print_metrics(average_metrics)

            print(f"URL: {url}")
            print(f"Number of calls: {loop_count}")
            print(f"Connection reuse: {reuse_connection}")
            print(f"Python total time: {time.time() - start_time - sleep_time}")
            print(f"Request total time: {total_time}")

        except KeyboardInterrupt:
            print("Exiting gracefully")

    elif background:
    # Loop forever
        try:
            while True:
                metrics = perform_http_request(url, method, curl, post_data)
                # Replace this print with just http status, url etc (for logging)
                print_metrics(metrics)
                if send_to_influx:
                    send_to_influxdb(url, metrics, influx_config)
                    # Can we catch and print the InfluxDB status here?
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Exiting gracefully")

    else:
    # Perform a single request
        try:
            metrics = perform_http_request(url, method, curl, post_data)
            print_metrics(metrics)
            if send_to_influx:
                send_to_influxdb(url, metrics, influx_config)
        except KeyboardInterrupt:
            print("Exiting gracefully")

if __name__ == "__main__":
    main()
