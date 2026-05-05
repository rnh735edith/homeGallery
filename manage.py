#!/usr/bin/env python
"""
HomeGallery Server Manager
Reliable server start/stop for Windows (handles spaces in Python path).

Usage:
    python manage.py start           # Start server in background
    python manage.py stop            # Stop all server processes
    python manage.py restart         # Stop and start
    python manage.py status          # Check if server is running
    python manage.py start --setup   # Force setup before starting
    python manage.py start --port 3000  # Custom port
"""

import os
import sys
import subprocess
import time
import json

repo_root = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(repo_root, "data", ".server.pid")


def ensure_data_dir():
    os.makedirs(os.path.join(repo_root, "data"), exist_ok=True)


def get_python_path():
    """Get the correct Python executable path."""
    return sys.executable


def find_server_pid():
    """Find server PID from PID file."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            # Quick check if process exists (platform-independent)
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["tasklist", "/FI", f"PID eq {pid}"],
                        capture_output=True, text=True, timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    return pid
                else:
                    os.kill(pid, 0)
                    return pid
            except Exception:
                pass
        except (ValueError, IOError):
            pass
    return None


def find_all_python_servers():
    """Find all Python processes running start.py."""
    pids = []
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["wmic", "process", "where", "name='python.exe'", "get", "ProcessId,CommandLine"],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in result.stdout.split("\n"):
                if "start.py" in line:
                    parts = line.strip().split()
                    for part in parts:
                        if part.isdigit():
                            pids.append(int(part))
                            break
        except Exception:
            pass
    return pids


def is_server_running(port=8080):
    """Check if server is responding on the given port."""
    try:
        import urllib.request
        url = f"http://localhost:{port}/health"
        req = urllib.request.urlopen(url, timeout=3)
        return req.status == 200
    except Exception:
        return False


def start_server(port=8080, setup=False):
    """Start server in background using subprocess."""
    if is_server_running(port):
        print(f"Server already running on port {port}")
        pid = find_server_pid()
        if pid:
            print(f"  PID: {pid}")
        return

    # Stop existing servers first
    stop_server()

    ensure_data_dir()

    python_path = get_python_path()
    start_script = os.path.join(repo_root, "start.py")

    cmd = [python_path, start_script]
    if setup:
        cmd.append("--setup")

    print(f"Starting server on port {port}...")
    print(f"  Python: {python_path}")
    print(f"  Script: {start_script}")

    # Create log file
    log_file = os.path.join(repo_root, "data", "server.log")

    # Open in detached process (Windows)
    if os.name == "nt":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        with open(log_file, "a") as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                cwd=repo_root,
            )
    else:
        with open(log_file, "a") as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                cwd=repo_root,
            )

    # Save PID
    with open(PID_FILE, "w") as f:
        f.write(str(process.pid))

    print(f"  Server started (PID: {process.pid})")
    print(f"  Logs: {log_file}")

    # Wait for server to be ready
    print("  Waiting for server to be ready...", end="", flush=True)
    for i in range(30):
        time.sleep(1)
        print(".", end="", flush=True)
        if is_server_running(port):
            print()
            print(f"  Server ready at http://localhost:{port}")
            return process.pid
    print()
    print("  Warning: Server may still be starting. Check logs.")
    return process.pid


def stop_server():
    """Stop all HomeGallery server processes."""
    # Kill by PID file
    pid = find_server_pid()
    if pid:
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                print(f"  Stopped server (PID: {pid})")
            else:
                os.kill(pid, 15)
                print(f"  Stopped server (PID: {pid})")
        except Exception as e:
            print(f"  Error stopping PID {pid}: {e}")

        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

    # Also kill any remaining start.py processes
    server_pids = find_all_python_servers()
    for p in server_pids:
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(p)],
                    capture_output=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                print(f"  Stopped server process (PID: {p})")
            else:
                os.kill(p, 15)
                print(f"  Stopped server process (PID: {p})")
        except Exception:
            pass


def restart_server(port=8080, setup=False):
    """Stop and start the server."""
    print("Stopping server...")
    stop_server()
    time.sleep(2)
    print("Starting server...")
    return start_server(port=port, setup=setup)


def status_server(port=8080):
    """Check server status."""
    running = is_server_running(port)
    pid = find_server_pid()

    print("Server Status:")
    print(f"  Responding: {'Yes' if running else 'No'}")
    print(f"  PID file: {pid if pid else 'None'}")

    if running:
        try:
            import urllib.request
            url = f"http://localhost:{port}/health"
            req = urllib.request.urlopen(url, timeout=3)
            data = json.loads(req.read().decode())
            print(f"  Health: {data.get('status', 'unknown')}")
            print(f"  Version: {data.get('version', 'unknown')}")
        except Exception:
            pass

    all_pids = find_all_python_servers()
    if all_pids:
        print(f"  Additional server processes: {all_pids}")


def print_help():
    """Print help message."""
    print(__doc__)
    print("\nExamples:")
    print("  python manage.py start              # Start server")
    print("  python manage.py start --port 3000  # Custom port")
    print("  python manage.py stop               # Stop server")
    print("  python manage.py restart            # Restart server")
    print("  python manage.py status             # Check status")


def main():
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print_help()
        return

    command = args[0]
    port = 8080
    setup = False

    # Parse additional args
    i = 1
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i] == "--setup":
            setup = True
            i += 1
        else:
            i += 1

    if command == "start":
        start_server(port=port, setup=setup)
    elif command == "stop":
        stop_server()
    elif command == "restart":
        restart_server(port=port, setup=setup)
    elif command == "status":
        status_server(port=port)
    else:
        print(f"Unknown command: {command}")
        print_help()


if __name__ == "__main__":
    main()
