# WITTACK — Cross-Platform Wi-Fi Verification & Audit Tool

![Alt text](assets/banner.jpg)
A localized, multi-platform command-line utility designed to audit Wi-Fi network credential resilience. The tool orchestrates native operating system networking stacks via subprocess pipelines to test password lists against designated SSIDs locally.

---
## ✨ Features

- **Network Discovery:** Scans nearby Wi-Fi networks and displays a cleanly numbered list.
- **Wordlist Support:** Iterates through passwords from a custom text file (`.txt`).
- **Speed Optimizations:**
  - Skips passwords shorter than 8 characters (WPA2 baseline requirement).
  - High-frequency connection polling every 0.2 seconds.
  - Aborts polling early on definitive authentication failures.
  - Defers profile deletions to minimize subprocess overhead.
- **Cross-Platform:** Native support across Windows, macOS, and Linux using built-in system tools.
- **Interactive UI:** Colored terminal output featuring a live progress counter.
- **Automated Logging:** Saves recovered credentials directly to `output.txt`.

---

## 🛠️ Requirements

- **Python:** Version 3.6 or higher.
- **Privileges:** Administrator or root access (required to modify OS network profiles).
- **External Dependencies:** Only one external library for colored terminal interfaces:
  ```bash
  pip install colorama

🏗️ Architecture & Flow Mechanics
---------------------------------

The application follows a structured, synchronous execution cycle managed through strict permission enforcement, platform discovery, and high-frequency state-checking loops.

```
[Main Entry]
    │
    ▼
[Enforce Admin Privileges] ───► (Windows: ctypes / Unix: os.execvp)
    │
    ▼
[Scan Nearby Interfaces]  ───► (Filters netsh / nmcli / airport outputs)
    │
    ▼
[Interactive Menu Selection]
    │
    ▼
[Optimized Password Iteration Stream]
    │
    ├── (Skip strings < 8 chars)
    └── [Subprocess Connection Handshake] ───► [Fast Polling Loop (0.2s)]
            │
            ├──► [True]  ──► Log to output.txt & Terminate
            └──► [False] ──► Immediate Profile Cleanup
```

⚙️ Low-Level Module Breakdowns
------------------------------

### 1\. Automated Privilege Elevation (`enforce_admin_privileges`)

Network profile modifications require advanced subsystem access across all operating systems. The script handles this seamlessly before initialization:

-   **Windows Subsystem:** Utilizes `ctypes.windll.shell32.IsUserAnAdmin()` to verify security tokens. If absent, it forces a User Account Control (UAC) prompt using `ShellExecuteW` with the `runas` parameter to relaunch the script within an elevated shell context.

-   **POSIX Subsystems (Linux/Darwin):** Evaluates `os.geteuid()`. If the effective user ID is non-root, it explicitly leverages `os.execvp` to replace the current process image with a clean `sudo` execution thread.

### 2\. Network Interface Discovery (`scan_wifi_networks`)

The script directly interfaces with standard OS management binaries, parsing raw strings into manageable data structures:

-   **Windows Platform:** Parses stdout tables from `netsh wlan show networks`, isolating lines containing key strings while stripping structural colon delimiters.

-   **Linux Platform:** Leverages `nmcli` in terse mode (`-t`) filtering directly for the `SSID` property to prevent excessive string manipulation.

-   **macOS Platform:** Invokes Apple's private wireless management framework binary (`airport -s`) and slices tabular column indices.

### 3\. Native Handshake Orchestration (`connect_wifi`)

Rather than relying on third-party network interface cards or heavy packet-injection drivers, the script manipulates native OS profile manager workflows:

-   **XML Profile Overwriting (Windows):** Dynamically builds a standard `WLANProfile` configuration using XML schemas. SSIDs and passwords are automatically escaped via `xml.sax.saxutils.escape` to maintain valid document syntax. This payload is stored inside a `tempfile.NamedTemporaryFile` and applied immediately via `netsh wlan add profile`, completely mitigating the overhead of scanning and deleting pre-existing network configurations.

-   **High-Frequency State Polling:** The Windows and macOS pipelines feature an aggressive `time.sleep(0.2)` polling gate restricted to 6 loops. This checks live system states continuously, enforcing an immediate break out of the thread if explicit failure messages (like `"authentication failed"`) are registered.

-   **Volatile Profile Cleanup:** To prevent the target machine's operating system from getting cluttered with stale network configurations, a cleanup routine automatically purges invalid connection definitions (`delete profile` / `removepreferredwirelessnetwork`) the moment a failure flag is verified.

🚀 Performance Optimizations
----------------------------

-   **Heuristic Length Skipping:** Instantly ignores any passphrase token under 8 characters using Python string evaluation (`len(word) < 8`), bypassing expensive system shell executions for combinations that violate base WPA2 specification constraints.

-   **Buffered I/O Console Throttling:** Terminal screen rewrites via `sys.stdout.write` are buffered to trigger exclusively on every 1,000 combinations, preventing standard terminal I/O latency from slowing down core loop speeds.

-   **Implicit Memory Management:** Uses context managers (`with open()`) using `errors='ignore'` parameters to handle unexpected malformed encoding errors seamlessly across large wordlists without interrupting loop integrity.

💻 How to Use
-------------

### Step 1: Prepare a password file

Create a plain text file (e.g., `passwords.txt`) containing one password candidate per line.

Plaintext

```
12345678
password123
mysecretkey

```

*Note: The tool automatically skips any entry under 8 characters to save execution cycles.*

### Step 2: Run the script with elevated privileges

**Windows:**

1.  Open **Command Prompt** as Administrator (Right-click -> *Run as administrator*).

2.  Navigate to the script's directory.

3.  Execute:

    DOS

    ```
    python wifi_tool.py

    ```

**macOS / Linux:**

1.  Open a terminal instance.

2.  Execute with `sudo`:

    Bash

    ```
    sudo python3 wifi_tool.py

    ```

### Step 3: Follow the interactive menu

1.  The script discovers visible interfaces and prints them dynamically:

    Plaintext

    ```
    Found 3 network(s):
    [0] MyHomeWiFi
    [1] GuestNetwork
    [2] OfficeWiFi

    ```

2.  Enter the index number corresponding to the target SSID (e.g., `0`).

3.  Provide the file path to your target wordlist (e.g., `./passwords.txt`).

4.  The loop starts executing, printing real-time iteration metrics:

    Plaintext

    ```
    Combinations Attempted: 1,000

    ```

### Step 4: Password Recovery

-   Upon a successful handshake, the correct credential is highlighted in green.

-   The entry is logged directly into `output.txt` within the execution directory.

-   Press **Enter** to cleanly terminate the script.

🔍 Troubleshooting
------------------

-   **Issue:** `"Failed to add profile"` on Windows

    -   **Solution:** Close the console, right-click your command prompt application, and select *Run as Administrator*.

-   **Issue:** No networks discovered

    -   **Solution:** Verify the host machine's Wi-Fi interface is enabled and not locked in Airplane mode.

-   **Issue:** `"nmcli not found"` on Linux systems

    -   **Solution:** Install the missing package via your native package manager (e.g., `sudo apt install network-manager`).

-   **Issue:** Script performance feels sluggish

    -   **Solution:** Operational speed is governed by hardware handshake limits. Filter down your wordlist size to more likely targets.

-   **Issue:** Known valid password fails to register

    -   **Solution:** Extend the timeout bounds. Inside the `connect_windows()` function block, change the loop evaluation boundary from `range(6)` to `range(10)`.

-   **Issue:** ANSI escape sequences break terminal layout on Windows

    -   **Solution:** Run the script within modern terminal environments (like Windows Terminal) or confirm `colorama.init()` initializes on start.

⚖️ Legal & Ethical Policy
-------------------------

This utility is architected exclusively for authorized infrastructure security auditing, local credential recovery, and educational systems research. Unauthorized targeting of networks without prior written owner validation is structurally unlawful and violates regional telecommunications access policies. For details on industry compliance standards and standard network auditing guidelines, consult official security framework practices online. The development maintainers accept no liability for operational misapplication.

📄 License
----------

This project is licensed under the [MIT License](https://www.google.com/search?q=LICENSE)---feel free to fork, modify, and distribute for all legitimate security auditing workflows.

**Happy (ethical) testing!**