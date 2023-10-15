# http_metrics_debugger

The HTTP Metrics Debugger is a small Python application that allows you to test and collect metrics for HTTP endpoints. It uses the `pycurl` library to perform HTTP requests.

There is also optional support for sending the metrics to an InfluxDBv2 database using the `influxdb-client`.

## Metrics Collected

The application collects the following metrics for each iteration:

- DNS Resolution Time
- Connection Time
- Time to First Byte (TTFB)
- Total Request Time
- AppConnect Time (TLS handshake time)
- HTTP Response Code

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
# gcc: Build the pycurl C-python module
# python3-venv: Python virtual environment support.
apt install git gcc python3-venv

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

### Example output:
```
Creating new connection
DNS Resolution Time: 0.00 seconds
AppConnect Time: 0.02 seconds
Connection Time: 0.01 seconds
Time to First Byte (TTFB): 0.08 seconds

Total Request Time: 0.08 seconds
Total Data Received: 18.09 KB
HTTP Response Code: 200
```

## Usage

The following command line arguments are available:

| Argument                  | Description                                   |
|---------------------------|-----------------------------------------------|
| `url`                     | The URL of the HTTP endpoint to test.        |
| `method`                  | The HTTP method to use (e.g., GET, POST).     |
| `--influx`                | Send metrics to InfluxDB database             |
| `-i`, `--interval`        | Interval between tests in seconds (default: 60). |
| `-l`, `--loop`            | Number of times to run the test (default: 1 time). |
| `-r`, `--connection-reuse`| Reuse the same HTTP connection for multiple requests (use the flag to enable). |
| `-d`, `--data`            | Data to include in the request body (for POST requests). |

**Example:**

```bash
# Full example:
python http_metrics.py https://example.com -i 5 -l 10 -r -x POST -d '{"key": "value"}'
```

## License

This application is distributed under the MIT License.

## Todo / Future improvements

* Add an option to log less
* Add Grafana dashboard
* Add support for specifying a configuration file