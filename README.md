# http_metrics_debugger

The HTTP Metrics Debugger is a small Python application that allows you to test and collect metrics for HTTP endpoints. It uses the `pycurl` library to perform HTTP requests using `libcurl` in the background.

The application can be used both as a command line tool to print statistics, but also as a background service with optional support for sending the metrics to an InfluxDBv2 database using the `influxdb-client`.

By running this as a background service, you can setup your own self-hosted Pingdom-style monitoring service.

**Example output:**
```
DNS Resolution Time: 0.00 seconds
Connection Time: 0.01 seconds
AppConnect Time: 0.02 seconds
Pre-transfer Time: 0.02 seconds
Time to First Byte (TTFB): 0.08 seconds

Total Request Time: 0.08 seconds
Total Data Received: 18.99 KB
HTTP Response Code: 200
---------------------------------
```

## Metrics Collected

The application collects all values available from the Pycurl object:

- DNS Resolution Time
- Connection Time
- AppConnect Time (TLS handshake time)
- Pre-transfer time
- Time to First Byte (Starttransfer)
- Total Request Time
- HTTP Response Code

For more info about the timings, see the Curl manual:  
https://curl.se/libcurl/c/curl_easy_getinfo.html

## Prerequisites

- Python 3.x
  - pycurl
  - influxdb-client
  - argparse
- InfluxDB 2.x (optional)

## Installation

The recommended approach is to use a Python virtual environment and launch the application with systemd (or in a Docker container).
```bash
# 1. Install Dependencies
# git: Clone this repo
# python3-venv: Python virtual environment support.
# gcc: Build the pycurl C-python module
# libcurl4-openssl-dev: Required to build pycurl
apt install git gcc python3-venv libcurl4-openssl-dev

# 2. Clone this repo
git clone https://github.com/sandnabba/http_metrics_debugger
cd http_metrics_debugger

# 3. Deploy Python virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Run:
python http_metrics.py https://www.google.com
```
## Usage

The following command line arguments are available:

| Argument                  | Description                                   |
|---------------------------|-----------------------------------------------|
| `url`                     | The URL of the HTTP endpoint to test.        |
| `method`                  | The HTTP method to use (e.g., GET, POST).     |
| `-c`, `--config`          | Configuration file |
| `--influx`                | Send metrics to InfluxDB database. Requires a configuration file.|
| `-i`, `--interval`        | Interval between tests in seconds (default: 60). |
| `-l`, `--loop`            | Number of times to run the test. If no number is provided, run infinite. (default: Single run). |
| `-r`, `--connection-reuse`| Reuse the same HTTP connection for multiple requests (use the flag to enable). |
| `-d`, `--data`            | Data to include in the request body (for POST requests). |
| `-b`, `--background`      | Run as background service. Run forever and print less logs. |

**Example:**

```bash
# Full example:
python http_metrics.py https://example.com -i 5 -l 10 -r -x POST -d '{"key": "value"}'
```

### Configuration file

See [`config.yml`](./config.yml)

## License

This application is distributed under the MIT License.

## Todo / Future improvements

* Add Grafana dashboard
* Systemd-file with templating
* Make Docker-container + Helm chart

## Other reading

Debugging HTTP calls with Chrome:  
https://blog.cloudflare.com/a-question-of-timing/