#!/usr/bin/env python
"""
HomeGallery One-Command Launcher
Installs dependencies, builds frontend, and starts the server.

Usage:
    python run.py                  # Install deps + build + start
    python run.py start            # Start server only
    python run.py start --setup    # Force setup wizard
    python run.py install          # Install dependencies only
    python run.py build            # Build frontend only
    python run.py --help           # Show help
"""

import os
import sys
import subprocess
import time

repo_root = os.path.dirname(os.path.abspath(__file__))


def ensure_data_dir():
    os.makedirs(os.path.join(repo_root, "data"), exist_ok=True)


def run_cmd(cmd, cwd=None, check=True):
    """Run a command and stream output."""
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or repo_root, check=check)
    return result.returncode == 0


def install_backend_deps():
    """Install Python dependencies."""
    print("\n[1/4] Installing backend dependencies...")
    req_file = os.path.join(repo_root, "backend", "requirements.txt")
    if os.path.exists(req_file):
        return run_cmd([sys.executable, "-m", "pip", "install", "-r", req_file, "-q"])
    print("  No requirements.txt found, skipping.")
    return True


def install_frontend_deps():
    """Install Node dependencies."""
    print("\n[2/4] Installing frontend dependencies...")
    frontend_dir = os.path.join(repo_root, "frontend")
    if os.path.exists(os.path.join(frontend_dir, "package.json")):
        npm = "npm.cmd" if os.name == "nt" else "npm"
        return run_cmd([npm, "install", "--quiet"], cwd=frontend_dir)
    print("  No package.json found, skipping.")
    return True


def build_frontend():
    """Build the frontend SPA."""
    print("\n[3/4] Building frontend...")
    frontend_dir = os.path.join(repo_root, "frontend")
    dist_dir = os.path.join(frontend_dir, "dist")
    if os.path.exists(os.path.join(frontend_dir, "package.json")):
        npm = "npm.cmd" if os.name == "nt" else "npm"
        success = run_cmd([npm, "run", "build"], cwd=frontend_dir)
        if success and os.path.exists(os.path.join(dist_dir, "index.html")):
            print(f"  Frontend built to {dist_dir}")
        return success
    print("  No package.json found, skipping.")
    return True


def start_server(setup=False):
    """Start the server (delegates to manage.py)."""
    print("\n[4/4] Starting server...")
    cmd = [sys.executable, os.path.join(repo_root, "manage.py"), "start"]
    if setup:
        cmd.append("--setup")
    return run_cmd(cmd)


def print_help():
    print(__doc__)


def main():
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print_help()
        return

    ensure_data_dir()

    command = args[0]
    setup = "--setup" in args

    if command == "install":
        install_backend_deps()
        install_frontend_deps()
    elif command == "build":
        install_frontend_deps()
        build_frontend()
    elif command == "start":
        start_server(setup=setup)
    else:
        # Default: full pipeline
        install_backend_deps()
        install_frontend_deps()
        build_frontend()
        start_server(setup=setup)


if __name__ == "__main__":
    main()
