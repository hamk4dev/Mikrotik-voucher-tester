# Mikrotik JSMD5 Login - HotSpot Voucher Tester

<p align="center">  
  <img src="https://hamkadev.wuaze.com/gambar/screenshot.png" alt="Screenshot Aplikasi" width="800" />  
</p>  

A professional testing tool for MikroTik HotSpot voucher authentication systems implementing the JavaScript MD5 challenge/response protocol.


---

## Overview

A professional Python-based tool for testing MikroTik HotSpot voucher authentication systems that implement the JavaScript MD5 challenge/response protocol commonly used by captive portals.


---

## Features

- Complete JS MD5 Implementation
Authentic challenge/response computation matching the portal’s JavaScript logic.

- Multi-factor Success Detection
Analyzes response content, headers, and redirects for accurate validation.

- Flexible Testing Modes
Supports both single voucher and bulk wordlist testing.

- Performance Optimized
Configurable timeouts and delays for efficient large-scale testing.

- Security Conscious
Full SSL/TLS support with proper error handling and safe connection management.

- Comprehensive Logging
Verbose mode available for detailed troubleshooting and debugging.

- PAP Fallback Support
Alternative authentication method when MD5 challenge fails or is unavailable.



---

## Installation

**Requirements**

· Python 3.8 or higher
· requests library

**Quick Setup**

```bash
pip install requests
pip install -r requirements.txt
```

---

## Usage Examples

**Single Voucher Test**

```bash
python3 mikrotik_jsmd5_loginv2.py -u http://192.168.88.1 --voucher "TEST123"
```

**Bulk Testing with Wordlist**

```bash
python3 mikrotik_jsmd5_loginv2.py -u https://hotspot.example.com -w vouchers.txt -o results.txt -d 1
```

**Verbose Debugging Mode**

```bash
python3 mikrotik_jsmd5_loginv2.py -u hotspot.company.com -w vouchers.txt -v -t 12
```

---

## Command Line Options

```bash
-u, --url  
Target portal URL (required)

--voucher 
Single voucher to test

-w, --wordlist 
Path to voucher wordlist file

-t, --timeout 
HTTP request timeout (seconds).  
Default: 8

-d, --delay
Delay between attempts (seconds).  
Default: 0

-o, --output
Save results to file

-v, --verbose  
Show detailed request/response logs  
Default: False

--no-progress 
Disable progress bar  
Default: False
```


---

## How It Works

The tool replicates the exact authentication flow of a web browser:

1. Page Retrieval – Fetches the captive portal login page.


2. Form Analysis – Extracts hidden fields and JavaScript challenges.


3. MD5 Computation – Reproduces the portal’s JavaScript MD5 algorithm.


4. Authentication – Submits credentials using proper challenge/response logic.


5. Result Analysis – Detects success through multiple verification methods.




---

## Output & Results

Successful authentications are displayed in real-time and optionally saved to a file.
In verbose mode, you can review complete details including:

- Request/response headers

- Computed hash values

- Form parameters

- Redirect chains

- Error messages



---

## Legal & Ethical Use

> ⚠️ Important Notice:
This tool is intended only for legitimate use, including:

- Testing your own networks

- Authorized penetration testing with          written permission

- Educational and research activities

- Always obtain explicit written authorization before testing any system you do not own.
The authors are not responsible for misuse of this tool.


---

## Contributing

Contributions are welcome!
Please ensure that you:

1. Clearly document all changes in pull requests.


2. Explain security-related modifications thoroughly.


3. Follow the existing code style and structure.




---

## License

MIT License – See the LICENSE file for full terms.


---

## Developer

Author: hamk4dev
Portfolio: https://hamkadev.wuaze.com


---
