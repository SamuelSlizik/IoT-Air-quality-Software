#!/usr/bin/env python3
import json
import subprocess
import time
from typing import Optional

# Paths to configuration files
SETTINGS_PATH = './settings.json'


def load_settings():
    """Load settings from the JSON file."""
    try:
        with open(SETTINGS_PATH, 'r') as f:
            settings = json.load(f)
        return settings
    except Exception as e:
        print(f"Error reading settings: {e}")
        return None


#!/usr/bin/env python3
"""
wifi_manager.py

Requires:
  - NetworkManager + nmcli installed and running.
  - Script run as root (sudo), so that nmcli can reconfigure interfaces.

Functions:
  - is_wifi_connected(interface: str = 'wlan0') → bool
      Returns True if the specified interface is associated with an SSID.

  - get_active_connection(interface: str = 'wlan0') → str
      Returns the NM connection name active on `interface`, or empty string if none.

  - get_connection_psk(connection: str) → Optional[str]
      Retrieves the WPA-PSK for a given NM connection name, or None if open or not set.

  - connect_wifi(ssid: str, password: Optional[str] = None,
                interface: str = 'wlan0', timeout: int = 30) → bool
      Connects to a Wi-Fi network via nmcli.
      If already connected to that SSID with an identical password, returns immediately.
      Otherwise, attempts (re)connection and waits up to `timeout` seconds.
      Returns True if connected, False on failure.

  - create_hotspot(ssid: str = 'Pi_AP', password: Optional[str] = None,
                   interface: str = 'wlan0') → bool
      Starts an access point on `interface` immediately.
      If hotspot with same SSID and password is already active, returns immediately.
      Otherwise, brings up the AP (WPA2 if password provided, open otherwise).
      Returns True on success, False otherwise.

  - is_hotspot_active(interface: str = 'wlan0') → bool
      Checks if `interface` is currently in Access Point (AP) mode.

All functions are idempotent: repeated calls with identical parameters won’t drop or reconfigure the network.
"""


def is_wifi_connected(interface: str = 'wlan0') -> bool:
    """
    Returns True if `interface` is currently associated with an SSID.
    """
    try:
        print("checking if wifi connected")
        result = subprocess.run(
            ['iwgetid', interface, '-r'],
            capture_output=True, text=True, check=False
        )
        return bool(result.stdout.strip())
    except FileNotFoundError:
        raise RuntimeError("iwgetid not found; ensure wireless-tools is installed")


def get_active_connection(interface: str = 'wlan0') -> str:
    """
    Returns the NetworkManager connection name active on `interface`, or '' if none.
    """
    try:
        print("getting active connection")
        res = subprocess.run(
            ['nmcli', '-t', '-f', 'NAME,DEVICE', 'connection', 'show', '--active'],
            capture_output=True, text=True, check=False
        )
        for line in res.stdout.splitlines():
            if ':' in line:
                name, dev = line.split(':', 1)
                if dev == interface:
                    return name
        return ''
    except FileNotFoundError:
        raise RuntimeError("nmcli not found; ensure NetworkManager is installed")


def get_connection_psk(connection: str) -> Optional[str]:
    """
    Retrieves the WPA-PSK for a given NM connection name, or None if open/not set.
    Requires root to read secrets.
    """
    try:
        print("getting psk")
        res = subprocess.run(
            ['nmcli', '-s', '-g', '802-11-wireless-security.psk', 'connection', 'show', connection],
            capture_output=True, text=True, check=False
        )
        psk = res.stdout.strip()
        return psk if psk else None
    except FileNotFoundError:
        raise RuntimeError("nmcli not found; ensure NetworkManager is installed")


def connect_wifi(
    ssid: str,
    password: Optional[str] = None,
    interface: str = 'wlan0',
    timeout: int = 30
) -> bool:
    """
    Connects to a Wi-Fi network via nmcli.
    Idempotent: returns immediately if already on SSID with same password.
    Otherwise attempts connection and waits up to `timeout` seconds.
    """
    current = get_active_connection(interface)
    if current == ssid and is_wifi_connected(interface):
        # Check that stored PSK matches provided
        stored = get_connection_psk(current)
        if stored == password:
            return True
    # Build and run nmcli command
    cmd = [
        'nmcli', 'device', 'wifi', 'connect', ssid,
        'ifname', interface
    ]
    if password:
        cmd += ['password', password]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return False
    for _ in range(timeout):
        if is_wifi_connected(interface):
            return True
        time.sleep(1)
    return False


def create_hotspot(
    ssid: str = 'IoTAQ',
    password: Optional[str] = None,
    interface: str = 'wlan0'
) -> bool:
    """
    Starts an access point on `interface` immediately.
    Idempotent: returns immediately if hotspot with same SSID and password is active.
    Otherwise brings up the AP (WPA2 if password provided, open otherwise).
    """
    print(f"creating hotspot with name:{ssid}, password:{password}, interface:{interface}")
    current = get_active_connection(interface)
    if current == ssid and is_hotspot_active(interface):
        stored = get_connection_psk(current)
        if stored == password:
            return True
    cmd = [
        'nmcli', 'device', 'wifi', 'hotspot',
        'ifname', interface,
        'con-name', ssid,
        'ssid', ssid
    ]
    if not password:
        password = "admin"
    cmd += ['password', password]
    print("running command to start hotspot")
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(f"{res.returncode}")
    return res.returncode == 0


def is_hotspot_active(
    interface: str = 'wlan0'
) -> bool:
    """
    Checks if `interface` is in Access Point (AP) mode via 'iw'.
    Returns True if in AP mode (hotspot active), False otherwise.
    """
    try:
        print("checking if hotspot active")
        res = subprocess.run(
            ['iw', 'dev', interface, 'info'],
            capture_output=True, text=True, check=False
        )
        for line in res.stdout.splitlines():
            if line.strip().startswith('type'):
                mode = line.strip().split()[1]
                return mode.lower() == 'ap'
        return False
    except FileNotFoundError:
        raise RuntimeError("iw not found; ensure wireless-tools/iw is installed")


def main():
    settings = load_settings()

    if not settings:
        print("No settings found starting hotspot")
        create_hotspot("IoTAQ", "admin")
        return

    force = settings.get("force_hotspot", "False")
    if force == "True" or force == True:
        print("Force hotspot found")
        create_hotspot(settings.get("hotspot_name", "IoTAQ"), settings.get("hotspot_password", "admin"))
        return

    if settings.get("wifi_name", None):
        print("Wifi name found, attempting connection")
        if connect_wifi(settings.get("wifi_name"), settings.get("wifi_password", None)):
            return

    print("Connection not successful, starting hotspot")
    create_hotspot(settings.get("hotspot_name", "IoTAQ"), settings.get("hotspot_password", "admin"))


if __name__ == '__main__':
    main()
