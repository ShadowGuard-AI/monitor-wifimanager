import argparse
import logging
import shutil
import subprocess
import re
import sys
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.
    """
    parser = argparse.ArgumentParser(description="Monitors Wi-Fi network connections and logs changes.",
                                     epilog="Encryption is read by running iwlist without sudo first. sudo iwlist is tried only as a fallback when the plain scan fails, and a failed scan still leaves the iwconfig fields in the record for that cycle.")
    parser.add_argument("-i", "--interface", dest="interface", help="Wi-Fi interface to monitor (e.g., wlan0)", required=True)
    parser.add_argument("-l", "--log_file", dest="log_file", default="wifi_monitor.log", help="Path to the log file (default: wifi_monitor.log)")
    parser.add_argument("-n", "--interval", dest="interval", type=int, default=5, help="Monitoring interval in seconds (default: 5)")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="Enable verbose logging (debug level)")
    return parser.parse_args()

def detect_encryption(iwlist_output):
    """
    Labels the encryption from scan output. WPA3, WPA2, WPA, and WEP
    markers are each tested, and a network is labelled open only when
    no marker is present at all.
    """
    if "WPA3" in iwlist_output:
        return "WPA3"
    if "WPA2" in iwlist_output:
        return "WPA2"
    if "WPA" in iwlist_output:
        return "WPA"
    if "WEP" in iwlist_output:
        return "WEP"
    if "Encryption key:on" in iwlist_output:
        return "WEP"
    return "Open"

def scan_encryption(interface):
    """
    Returns the encryption label from an iwlist scan, or None when the
    scan fails or returns nothing. The scan runs without sudo first;
    sudo is tried only as a fallback when the plain scan fails.
    """
    for command in (["iwlist", interface, "scanning"],
                    ["sudo", "iwlist", interface, "scanning"]):
        try:
            output = subprocess.check_output(command, universal_newlines=True, stderr=subprocess.DEVNULL)
            if output and output.strip():
                return detect_encryption(output)
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return None

def get_wifi_info(interface, previous_info=None):
    """
    Retrieves Wi-Fi network information using subprocess calls.

    Args:
        interface (str): The Wi-Fi interface to monitor.
        previous_info (dict): The previous cycle record, used to decide
            whether scan data needs to be fetched again.

    Returns:
        dict: SSID, BSSID, signal strength, and encryption type, or None
        when iwconfig itself fails. A failed scan is a partial result:
        the iwconfig fields are kept and the encryption is reported as
        the previous value, or Unknown when there is none.
    """
    try:
        iwconfig_output = subprocess.check_output(["iwconfig", interface], universal_newlines=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing command: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None

    ssid_match = re.search(r'ESSID:"(.*?)"', iwconfig_output)
    ssid = ssid_match.group(1) if ssid_match else "Not Connected"

    bssid_match = re.search(r'Access Point: (([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})', iwconfig_output)
    bssid = bssid_match.group(1) if bssid_match else "N/A"

    signal_level_match = re.search(r'Signal level=(-\d+) dBm', iwconfig_output)
    signal_level = signal_level_match.group(1) if signal_level_match else "N/A"

    if signal_level == "N/A":
        signal_level_match = re.search(r'Signal quality=.*?dBm', iwconfig_output)
        if signal_level_match:
            signal_level_match2 = re.search(r'(-?\d+)', signal_level_match.group(0))
            signal_level = signal_level_match2.group(1) if signal_level_match2 else "N/A"

    # Fetch scan data only when the SSID or BSSID changed, or when no
    # encryption value has been recorded yet.
    needs_scan = (previous_info is None
                  or previous_info.get("SSID") != ssid
                  or previous_info.get("BSSID") != bssid
                  or previous_info.get("Encryption") in (None, "Unknown"))
    if needs_scan:
        encryption = scan_encryption(interface)
        if encryption is None:
            logging.warning("iwlist scan failed; keeping the iwconfig fields and reporting encryption as unknown for this cycle.")
            encryption = previous_info.get("Encryption", "Unknown") if previous_info else "Unknown"
    else:
        encryption = previous_info.get("Encryption", "Unknown")

    return {
        "SSID": ssid,
        "BSSID": bssid,
        "Signal Strength": signal_level,
        "Encryption": encryption
    }

def main():
    """
    Main function to monitor Wi-Fi connections and log changes.
    """
    args = setup_argparse()

    if args.interval <= 0:
        logging.error("Error: Interval must be a positive integer.")
        print("Error: Interval must be a positive integer.")
        return 1

    if shutil.which("iwconfig") is None:
        logging.error("Error: iwconfig is not available on this machine, so no Wi-Fi information can be read.")
        print("Error: iwconfig is not available on this machine, so no Wi-Fi information can be read.")
        return 1

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.info("Starting Wi-Fi monitor...")
    logging.debug(f"Monitoring interface: {args.interface}, Logging to: {args.log_file}, Interval: {args.interval} seconds")

    previous_info = None

    try:
        while True:
            wifi_info = get_wifi_info(args.interface, previous_info)

            if wifi_info:
                if previous_info is None:
                    changed_fields = list(wifi_info.keys())
                else:
                    changed_fields = [field for field in wifi_info if wifi_info[field] != previous_info.get(field)]

                if changed_fields:
                    log_message = f"Wi-Fi Change Detected: Changed fields: {', '.join(changed_fields)}\n" \
                                  f"  SSID: {wifi_info['SSID']}\n" \
                                  f"  BSSID (MAC): {wifi_info['BSSID']}\n" \
                                  f"  Signal Strength: {wifi_info['Signal Strength']} dBm\n" \
                                  f"  Encryption: {wifi_info['Encryption']}"

                    logging.info(log_message)

                    with open(args.log_file, "a") as f:
                        f.write(log_message + "\n")

                    previous_info = wifi_info
            else:
                logging.warning("Could not retrieve Wi-Fi information.")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        logging.info("Wi-Fi monitor stopped by user.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return 1
    finally:
        logging.info("Exiting Wi-Fi monitor.")
    return 0

if __name__ == "__main__":
    # Example usage:
    # 1. Basic usage, monitor wlan0 every 5 seconds and log to wifi_monitor.log: python3 main.py -i wlan0
    # 2. Verbose logging: python3 main.py -i wlan0 -v
    # 3. Custom log file and interval: python3 main.py -i wlan0 -l custom_log.txt -n 10
    # Note: change logging only. Telling a changed network apart from an
    # operator's own intended roaming would require a database of known
    # good access points, which is outside the scope of basic monitoring.
    sys.exit(main())
