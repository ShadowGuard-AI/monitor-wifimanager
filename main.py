import argparse
import logging
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
    parser = argparse.ArgumentParser(description="Monitors Wi-Fi network connections and logs changes.")
    parser.add_argument("-i", "--interface", dest="interface", help="Wi-Fi interface to monitor (e.g., wlan0)", required=True)
    parser.add_argument("-l", "--log_file", dest="log_file", default="wifi_monitor.log", help="Path to the log file (default: wifi_monitor.log)")
    parser.add_argument("-n", "--interval", dest="interval", type=int, default=5, help="Monitoring interval in seconds (default: 5)")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="Enable verbose logging (debug level)")
    return parser.parse_args()

def get_wifi_info(interface):
    """
    Retrieves Wi-Fi network information using subprocess calls.

    Args:
        interface (str): The Wi-Fi interface to monitor.

    Returns:
        dict: A dictionary containing SSID, MAC address (BSSID), signal strength, and encryption type, or None if an error occurs.
    """
    try:
        # Use iwconfig to get Wi-Fi information
        iwconfig_output = subprocess.check_output(["iwconfig", interface], universal_newlines=True, stderr=subprocess.DEVNULL)

        # Extract SSID
        ssid_match = re.search(r'ESSID:"(.*?)"', iwconfig_output)
        ssid = ssid_match.group(1) if ssid_match else "Not Connected"

        # Extract BSSID (MAC Address)
        bssid_match = re.search(r'Access Point: (([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})', iwconfig_output)
        bssid = bssid_match.group(1) if bssid_match else "N/A"

        # Extract Signal Level
        signal_level_match = re.search(r'Signal level=(-\d+) dBm', iwconfig_output)
        signal_level = signal_level_match.group(1) if signal_level_match else "N/A"
        
        #Try newer versions of iwconfig output
        if signal_level == "N/A":
            signal_level_match = re.search(r'Signal quality=.*?dBm', iwconfig_output)
            if signal_level_match:
                signal_level_match2 = re.search(r'(-?\d+)', signal_level_match.group(0))
                signal_level = signal_level_match2.group(1) if signal_level_match2 else "N/A"

        # Use iwlist to get encryption information (requires sudo)
        iwlist_output = subprocess.check_output(["sudo", "iwlist", interface, "scanning"], universal_newlines=True, stderr=subprocess.DEVNULL)

        # Extract Encryption Type
        encryption_match = re.search(r'IE: IEEE 802.11i/WPA2 Version 1', iwlist_output)
        encryption = "WPA2" if encryption_match else "Open/WEP/Unknown" # Defaulting to WPA2 as more secure is the more probable

        return {
            "SSID": ssid,
            "BSSID": bssid,
            "Signal Strength": signal_level,
            "Encryption": encryption
        }
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing command: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None

def main():
    """
    Main function to monitor Wi-Fi connections and log changes.
    """
    args = setup_argparse()

    # Configure logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.info("Starting Wi-Fi monitor...")
    logging.debug(f"Monitoring interface: {args.interface}, Logging to: {args.log_file}, Interval: {args.interval} seconds")

    previous_ssid = None
    previous_bssid = None

    try:
        while True:
            wifi_info = get_wifi_info(args.interface)

            if wifi_info:
                current_ssid = wifi_info["SSID"]
                current_bssid = wifi_info["BSSID"]

                if current_ssid != previous_ssid or current_bssid != previous_bssid:
                    log_message = f"Wi-Fi Change Detected:\n" \
                                  f"  SSID: {current_ssid}\n" \
                                  f"  BSSID (MAC): {current_bssid}\n" \
                                  f"  Signal Strength: {wifi_info['Signal Strength']} dBm\n" \
                                  f"  Encryption: {wifi_info['Encryption']}"

                    logging.info(log_message)

                    # Save the log message to the log file
                    with open(args.log_file, "a") as f:
                        f.write(log_message + "\n")
                    
                    previous_ssid = current_ssid
                    previous_bssid = current_bssid
            else:
                logging.warning("Could not retrieve Wi-Fi information.")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        logging.info("Wi-Fi monitor stopped by user.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        logging.info("Exiting Wi-Fi monitor.")

if __name__ == "__main__":
    #Example usage:
    #1. Basic usage, monitor wlan0 every 5 seconds and log to wifi_monitor.log: python main.py -i wlan0
    #2. Verbose logging: python main.py -i wlan0 -v
    #3. Custom log file and interval: python main.py -i wlan0 -l custom_log.txt -n 10
    #Offensive tool note:  Detection of rogue access points would require a database of known good access points and comparing against them.  This is outside the scope of basic monitoring.
    main()