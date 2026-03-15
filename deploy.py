#!/usr/bin/env python3
import subprocess
import time
import sys
import re
import signal

# ==============================================================================
# Django + Cloudflare Tunnel Deployment Script
# ==============================================================================

PORT = 8000
HOST = "0.0.0.0"

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

django_process = None
tunnel_process = None

def cleanup(signum=None, frame=None):
    print(f"\n{Colors.YELLOW}Shutting down processes...{Colors.RESET}")
    if tunnel_process:
        print("Stopping Cloudflare Tunnel...")
        tunnel_process.terminate()
        try:
            tunnel_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            tunnel_process.kill()
            
    if django_process:
        print("Stopping Django Server...")
        django_process.terminate()
        try:
            django_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            django_process.kill()
    sys.exit(0)

# Register signals for cleanup
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    global django_process, tunnel_process

    print(f"{Colors.YELLOW}Starting Deployment...{Colors.RESET}")

    # 1. Check if cloudflared is installed
    try:
        subprocess.run(["cloudflared", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"{Colors.RED}Error: cloudflared is not installed.{Colors.RESET}")
        print("Install it using: brew install cloudflared")
        sys.exit(1)

    # 2. Start the Django Server
    print(f"{Colors.YELLOW}Starting Django Server on {HOST}:{PORT}...{Colors.RESET}")
    # Run the Django server and pipe its output so we can monitor or log it if needed
    django_process = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"{HOST}:{PORT}"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )

    # Give Django a moment to start
    time.sleep(3)
    if django_process.poll() is not None:
        print(f"{Colors.RED}Failed to start Django server.{Colors.RESET}")
        sys.exit(1)
        
    print(f"{Colors.GREEN}Django Server is running (PID: {django_process.pid}){Colors.RESET}")

    # 3. Start Cloudflare Tunnel
    print(f"{Colors.YELLOW}Starting Cloudflare Tunnel...{Colors.RESET}")
    
    tunnel_process = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{PORT}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    print(f"\n{Colors.YELLOW}Waiting for tunnel URL...{Colors.RESET}")

    # 4. Extract URL from output
    url_found = False
    url_pattern = re.compile(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com')

    # Read output non-blocking or just iterate over lines
    for line in tunnel_process.stdout:
        sys.stdout.write(line) # Echo cloudflared output to terminal
        sys.stdout.flush()
        
        match = url_pattern.search(line)
        if match and not url_found:
            url = match.group(0)
            print(f"\n{Colors.GREEN}{'='*60}")
            print(f"🚀 SERVER IS LIVE!")
            print(f"Public URL: {Colors.YELLOW}{url}{Colors.GREEN}")
            print(f"{'='*60}{Colors.RESET}\n")
            url_found = True
            # Don't break here, keep echoing output in case of errors/reconnects

    # If the process ends unexpectedly
    if tunnel_process.poll() is not None:
        print(f"{Colors.RED}Cloudflare Tunnel exited unexpectedly.{Colors.RESET}")
        cleanup()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cleanup()
