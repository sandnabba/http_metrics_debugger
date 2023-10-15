import pycurl
import io
import sys
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import argparse
import time

# InfluxDB 2.x configuration
INFLUXDB_URL = "http://your_influxdb_host:8086"
INFLUXDB_TOKEN = "your_influxdb_token"
INFLUXDB_ORG = "your_influxdb_org"
INFLUXDB_BUCKET = "your_influxdb_bucket"

def send_to_influxdb(url, metrics):
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    # Create a data point with the URL as a tag
    point = Point("http_metrics") \
        .tag("url", url) \
        .field("dns_resolution_time", metrics["dns_resolution_time"]) \
        .field("connection_time", metrics["connection_time"]) \
        .field("ttfb_time", metrics["ttfb_time"]) \
        .field("total_request_time", metrics["total_request_time"]) \
        .field("data_received_kb", metrics["data_received_kb"]) \
        .field("appconnect_time", metrics["appconnect_time"]) \
        .field("response_code", metrics["response_code"]) \
        .time(datetime.utcnow())

    # Write the data point to InfluxDB
    write_api.write(INFLUXDB_BUCKET, INFLUXDB_ORG, point)

def perform_http_request(url, method, curl, post_data=None):
    if curl is None:
        print("Creating new connection")
        # Create a pycurl.Curl object
        c = pycurl.Curl()
    else:
        print("Using existing object")
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
    ttfb_time = c.getinfo(pycurl.STARTTRANSFER_TIME)
    total_request_time = c.getinfo(pycurl.TOTAL_TIME)
    appconnect_time = c.getinfo(pycurl.APPCONNECT_TIME)
    data_received = c.getinfo(pycurl.SIZE_DOWNLOAD)  # Total data received
    response_code = c.getinfo(pycurl.RESPONSE_CODE)

    if curl is None:
        # Clean up the pycurl.Curl object
        c.close()

    return {
        "dns_resolution_time": dns_resolution_time,
        "connection_time": connection_time,
        "ttfb_time": ttfb_time,
        "total_request_time": total_request_time,
        "appconnect_time": appconnect_time,
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
    print(f"AppConnect Time: {metrics['appconnect_time']:.2f} seconds")
    print(f"Connection Time: {metrics['connection_time']:.2f} seconds")
    print(f"Time to First Byte (TTFB): {metrics['ttfb_time']:.2f} seconds")
    print("")
    print(f"Total Request Time: {metrics['total_request_time']:.2f} seconds")
    print(f"Total Data Received: {metrics['data_received_kb']:.2f} KB")
    print(f"HTTP Response Code: {metrics['response_code']}")

    print("---------------------------------\n")

def main():
    parser = argparse.ArgumentParser(description="HTTP endpoint testing and metrics collection")
    parser.add_argument("url", help="The URL to test")
    parser.add_argument("-x", "--method", type=str, default="GET", help="HTTP method to use, e.g.GET, POST. (Default: GET)")
    parser.add_argument("-i", "--interval", type=int, default=0, help="Interval between tests in seconds (default: None)")
    parser.add_argument("-l", "--loop", type=int, default=None, help="Number of times to run (default: 1 time)")
    parser.add_argument("-r", "--reuse-connection", action="store_true", default=False, help="Reuse the same HTTP connection")
    parser.add_argument("--influx", action="store_true", default=False, help="Send metrics to InfluxDB")
    parser.add_argument("-d", "--data", type=str, default=None, help="Data to include in the request body (for POST requests)")

    args = parser.parse_args()
    url = args.url
    method = args.method
    interval = args.interval
    loop_count = args.loop
    reuse_connection = args.reuse_connection
    send_to_influx = args.influx
    post_data = args.data

    start_time = time.time()

    if reuse_connection:
        print("Reusing connections!")
        curl = pycurl.Curl()
    else:
        curl = None

    if loop_count is not None:
        total_time = 0
        metrics_sum = {
            "dns_resolution_time": 0,
            "connection_time": 0,
            "ttfb_time": 0,
            "total_request_time": 0,
            "appconnect_time": 0,
            "data_received_kb": 0,
            "response_code": 0
        }

        try:
            for r in range(loop_count):
                metrics = perform_http_request(url, method, curl, post_data)
                print_metrics(metrics, loop_count=r)
                if send_to_influx:
                    send_to_influxdb(url, metrics)
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
    else:
        try:
            metrics = perform_http_request(url, method, curl, post_data)
            print_metrics(metrics)
            if send_to_influx:
                send_to_influxdb(url, metrics)
        except KeyboardInterrupt:
            print("Exiting gracefully")

if __name__ == "__main__":
    main()
