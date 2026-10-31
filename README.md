![Banner](banner.png)

# monitor-wifimanager
Monitors changes in Wi-Fi network connections, logging SSID, MAC address of the access point, signal strength, and encryption type whenever any of those fields changes. This is change logging only: the tool does not tell a changed network apart from the operator's own intended roaming. - Focused on System monitoring and alerts

The tool uses only the Python standard library. The system prerequisites are the `iwconfig` and `iwlist` executables (from the wireless-tools package): if `iwconfig` is not available, the tool prints that it cannot read Wi-Fi information and exits 1 at startup. Encryption is read by running `iwlist` without sudo first. `sudo iwlist` is tried only as a fallback when the plain scan fails, and a failed scan is kept as a partial record with the iwconfig fields and the encryption reported as unknown.

## Install
`git clone https://github.com/ShadowGuardAI/monitor-wifimanager`

## Usage
`python3 main.py -i <interface> [params]`

## Parameters
- `-h`: Show help message and exit
- `-i`, `--interface`: Wi-Fi interface to monitor (e.g., wlan0). Required.
- `-l`, `--log_file`: Path to the log file (default: wifi_monitor.log)
- `-n`, `--interval`: Monitoring interval in seconds (default: 5). Must be positive; a non positive value exits 1 at startup.
- `-v`, `--verbose`: Enable verbose logging (debug level)

## License
Copyright (c) ShadowGuardAI
