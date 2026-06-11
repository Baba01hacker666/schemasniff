import requests
import argparse
import sys
import json
import re
import time
import urllib3
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

# Disable insecure request warnings if user uses proxies/self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

BANNER = r"""
  ____       _                          _____       _  __  __ 
 / ___|  ___| |__   ___ _ __ ___   __ _/ ___| _ __ (_)/ _|/ _|
 \___ \ / __| '_ \ / _ \ '_ ` _ \ / _` \___ \| '_ \| | |_| |_ 
  ___) | (__| | | |  __/ | | | | | (_| |___) | | | | |  _|  _|
 |____/ \___|_| |_|\___|_| |_| |_|\__,_|____/|_| |_|_|_| |_|  
    
    GraphQL Schema Reconstructor via Field Bruteforce
    Made by baba01hacker
"""

def extract_messages(obj):
    """Recursively extract all 'message' fields from a JSON object."""
    messages = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "message" and isinstance(v, str):
                messages.append(v)
            else:
                messages.extend(extract_messages(v))
    elif isinstance(obj, list):
        for item in obj:
            messages.extend(extract_messages(item))
    return messages

class SchemaSniffer:
    def __init__(self, args):
        self.url = args.url
        self.method = args.method.upper()
        self.headers = {"Content-Type": "application/json"}
        self.timeout = args.timeout
        self.delay = args.delay
        self.proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None
        self.verify_ssl = not args.insecure
        self.threads = args.threads
        self.output_file = args.output
        
        if args.headers:
            for h in args.headers:
                if ":" in h:
                    k, v = h.split(":", 1)
                    self.headers[k.strip()] = v.strip()
                    
        if args.user_agent:
            self.headers["User-Agent"] = args.user_agent
        elif "User-Agent" not in self.headers:
            self.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SchemaSniff/1.0"

        self.discovered_fields = set()
        self.lock = threading.Lock()
        self.total_words = 0
        self.processed_words = 0

    def print_success(self, msg):
        print(f"{Colors.OKGREEN}[+]{Colors.ENDC} {msg}")

    def print_info(self, msg):
        print(f"{Colors.OKBLUE}[*]{Colors.ENDC} {msg}")

    def print_warning(self, msg):
        print(f"{Colors.WARNING}[!]{Colors.ENDC} {msg}")

    def print_error(self, msg):
        print(f"{Colors.FAIL}[-]{Colors.ENDC} {msg}")

    def test_field(self, word):
        if not word:
            return
            
        if self.delay > 0:
            time.sleep(self.delay)

        query = f"query {{ {word} }}"
        payload = {"query": query}
        
        try:
            if self.method == "GET":
                response = requests.get(
                    self.url, params=payload, headers=self.headers, 
                    timeout=self.timeout, proxies=self.proxies, verify=self.verify_ssl
                )
            else:
                response = requests.post(
                    self.url, json=payload, headers=self.headers, 
                    timeout=self.timeout, proxies=self.proxies, verify=self.verify_ssl
                )
                
            try:
                data = response.json()
            except ValueError:
                return
                
            messages = extract_messages(data.get("errors", []))
            if not messages:
                messages = extract_messages(data)
                
            new_discoveries = []
            
            for msg in messages:
                msg_lower = msg.lower()
                
                # 1. Did you mean suggestions
                if "did you mean" in msg_lower:
                    idx = msg_lower.find("did you mean")
                    suggestion_part = msg[idx + 12:]
                    suggested = re.findall(r'["\']([^"\']+)["\']', suggestion_part)
                    for s in suggested:
                        with self.lock:
                            if s not in self.discovered_fields:
                                self.discovered_fields.add(s)
                                new_discoveries.append(f"Discovered via suggestion: {Colors.BOLD}{s}{Colors.ENDC}")
                                
                # Identify if the message says this field doesn't exist
                unknown_phrases = ["cannot query field", "unknown field", "not found in type", "doesn't exist"]
                is_unknown = any(p in msg_lower for p in unknown_phrases)

                if not is_unknown:
                    # 2. Subfields required
                    if "subfields" in msg_lower:
                        with self.lock:
                            if word not in self.discovered_fields:
                                self.discovered_fields.add(word)
                                new_discoveries.append(f"Object field (needs subfields): {Colors.BOLD}{word}{Colors.ENDC}")
                                
                    # 3. Missing arguments
                    elif "is required" in msg_lower or "not provided" in msg_lower or "argument" in msg_lower:
                        with self.lock:
                            if word not in self.discovered_fields:
                                self.discovered_fields.add(word)
                                new_discoveries.append(f"Valid field (missing args): {Colors.BOLD}{word}{Colors.ENDC}")

                    # 4. Auth errors
                    else:
                        auth_keywords = ["authorized", "authenticated", "permission", "access", "forbidden"]
                        if any(k in msg_lower for k in auth_keywords) and word.lower() in msg_lower:
                            with self.lock:
                                if word not in self.discovered_fields:
                                    self.discovered_fields.add(word)
                                    new_discoveries.append(f"Restricted field (auth required): {Colors.BOLD}{word}{Colors.ENDC}")

            # 5. Field actually returned data
            if "data" in data and isinstance(data["data"], dict):
                if word in data["data"]:
                    with self.lock:
                        if word not in self.discovered_fields:
                            self.discovered_fields.add(word)
                            new_discoveries.append(f"Valid active field: {Colors.BOLD}{word}{Colors.ENDC}")
                            
            for discovery in new_discoveries:
                self.print_success(discovery)

        except requests.RequestException:
            pass
            
        with self.lock:
            self.processed_words += 1
            sys.stdout.write(f"\r{Colors.OKCYAN}[Status]{Colors.ENDC} Progress: {self.processed_words}/{self.total_words} ({len(self.discovered_fields)} fields found)")
            sys.stdout.flush()

    def run(self, wordlist_path):
        if wordlist_path:
            try:
                with open(wordlist_path, "r", encoding="utf-8") as f:
                    words = list(set([line.strip() for line in f if line.strip()]))
            except FileNotFoundError:
                self.print_error(f"Wordlist {wordlist_path} not found.")
                sys.exit(1)
        else:
            import os
            default_wordlist = os.path.join(os.path.dirname(__file__), "wordlist.txt")
            try:
                with open(default_wordlist, "r", encoding="utf-8") as f:
                    words = list(set([line.strip() for line in f if line.strip()]))
            except FileNotFoundError:
                self.print_error("Default wordlist.txt not found in package.")
                sys.exit(1)

        self.total_words = len(words)
        self.print_info(f"Targeting: {self.url}")
        self.print_info(f"Loaded {self.total_words} unique words.")
        self.print_info(f"Threads: {self.threads} | Timeout: {self.timeout}s")
        print("-" * 50)

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [executor.submit(self.test_field, word) for word in words]
            for _ in as_completed(futures):
                pass
                
        print("\n" + "-" * 50)
        self.print_success(f"Reconstruction Complete. Found {len(self.discovered_fields)} fields.")
        
        if self.discovered_fields:
            for field in sorted(self.discovered_fields):
                print(f"  - {field}")
                
        if self.output_file and self.discovered_fields:
            try:
                with open(self.output_file, "w", encoding="utf-8") as f:
                    if self.output_file.endswith(".json"):
                        json.dump({"endpoint": self.url, "fields": sorted(list(self.discovered_fields))}, f, indent=4)
                    else:
                        for field in sorted(self.discovered_fields):
                            f.write(f"{field}\n")
                self.print_info(f"Results saved to {self.output_file}")
            except Exception as e:
                self.print_error(f"Failed to write output: {str(e)}")

def main():
    print(Colors.OKCYAN + BANNER + Colors.ENDC)
    parser = argparse.ArgumentParser(description="SchemaSniff - Professional GraphQL Schema Reconstructor")
    
    # Required
    parser.add_argument("-u", "--url", required=True, help="Target GraphQL endpoint URL")
    parser.add_argument("-w", "--wordlist", required=False, help="Wordlist for field bruteforcing (defaults to built-in list)")
    
    # Request configuration
    req_group = parser.add_argument_group("Request Options")
    req_group.add_argument("-m", "--method", default="POST", choices=["GET", "POST"], help="HTTP Method (default: POST)")
    req_group.add_argument("-H", "--headers", nargs="*", help="Custom headers (e.g. 'Authorization: Bearer token')")
    req_group.add_argument("-A", "--user-agent", help="Custom User-Agent string")
    req_group.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds (default: 10)")
    
    # Performance
    perf_group = parser.add_argument_group("Performance & Throttling")
    perf_group.add_argument("-t", "--threads", type=int, default=10, help="Number of concurrent threads (default: 10)")
    perf_group.add_argument("--delay", type=float, default=0, help="Delay between requests in seconds (default: 0)")
    
    # Network & Output
    net_group = parser.add_argument_group("Network & Output")
    net_group.add_argument("-x", "--proxy", help="HTTP/HTTPS proxy (e.g. http://127.0.0.1:8080)")
    net_group.add_argument("-k", "--insecure", action="store_true", help="Disable SSL/TLS certificate verification")
    net_group.add_argument("-o", "--output", help="Output file to save discovered fields (supports .json and .txt)")

    args = parser.parse_args()
    
    sniffer = SchemaSniffer(args)
    try:
        sniffer.run(args.wordlist)
    except KeyboardInterrupt:
        print("\n")
        sniffer.print_warning("Execution interrupted by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()
