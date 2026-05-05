#!/usr/bin/env python
"""
HomeGallery Launcher

Usage:
    python start.py              # Start server (runs setup if first time)
    python start.py --setup    # Force re-run setup wizard
    python start.py --port 3000  # Override port
    python start.py --no-browser # Skip auto-opening browser
    python start.py --mcp       # Start Playwright MCP browser on port 8081
    python start.py --nginx      # Start Nginx reverse proxy
    python start.py --all      # Start app + MCP + Nginx
"""

import argparse
import os
import sys
import time
import threading
import subprocess
import signal

repo_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, repo_root)
sys.path.insert(0, os.path.join(repo_root, "backend"))


def check_config():
    try:
        from backend.app.config_loader import config_loader
        return config_loader.exists
    except ImportError:
        return False


def start_server(port=8080, host="0.0.0.0"):
    os.environ.setdefault("PORT", str(port))
    os.environ.setdefault("HOST", host)

    print(f"Starting HomeGallery server on {host}:{port}")

    try:
        import uvicorn
        uvicorn.run(
            "backend.app.main:app",
            host=host,
            port=port,
            reload=False,
        )
    except ImportError:
        os.system(f"{sys.executable} -m uvicorn backend.app.main:app --host {host} --port {port}")


def start_playwright_mcp(port=8081):
    print(f"Starting Playwright MCP browser on port {port}")

    npm = "npm.cmd" if os.name == "nt" else "npx"
    cmd = [npm, "-y", "@playwright/mcp@latest"]

    env = os.environ.copy()
    env["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = ""

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        print(f"Playwright MCP started (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"Error starting Playwright MCP: {e}")
        return None


def start_nginx(config_path=None):
    nginx = "nginx" if os.name != "nt" else "nginx.exe"

    print("Starting Nginx reverse proxy")

    cmd = [nginx, "-c", config_path] if config_path else [nginx]

    try:
        subprocess.run(cmd, check=True)
        print("Nginx started")
        return True
    except FileNotFoundError:
        print("Nginx not found. Install Nginx or add to PATH.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Nginx error: {e}")
        return False


def check_nginx_installed():
    nginx = "nginx" if os.name != "nt" else "nginx.exe"
    try:
        subprocess.run([nginx, "-v"], capture_output=True, check=True)
        return True
    except FileNotFoundError:
        return False
    except subprocess.CalledProcessError:
        return True
    return False


def generate_nginx_config(app_port=8080, mcp_port=8081):
    return f'''worker_processes 1;
error_log logs/nginx_error.log;
pid logs/nginx.pid;

events {{
    worker_connections 1024;
}}

http {{
    include       mime.types;
    default_type application/octet-stream;

    sendfile        on;
    keepalive_timeout 65;

    # Upstream for HomeGallery app
    upstream app_backend {{
        server 127.0.0.1:{app_port};
    }}

    # Upstream for Playwright MCP
    upstream mcp_backend {{
        server 127.0.0.1:{mcp_port};
    }}

    # HTTP server
    server {{
        listen 80;
        server_name localhost;

        location / {{
            proxy_pass http://app_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}

        location /mcp/ {{
            proxy_pass http://mcp_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }}

        location /api/ {{
            proxy_pass http://app_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}
    }}

    # HTTPS server (self-signed cert for production)
    server {{
        listen 443 ssl;
        server_name localhost;

        ssl_certificate ssl/server.crt;
        ssl_certificate_key ssl/server.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        location / {{
            proxy_pass http://app_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
        }}

        location /mcp/ {{
            proxy_pass http://mcp_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }}

        location /api/ {{
            proxy_pass http://app_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
        }}
    }}
}}
'''


def main():
    parser = argparse.ArgumentParser(description="HomeGallery Server Launcher")
    parser.add_argument("--setup", action="store_true", help="Force re-run setup wizard")
    parser.add_argument("--port", type=int, default=None, help="Server port")
    parser.add_argument("--host", type=str, default=None, help="Server host")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    parser.add_argument("--mcp", action="store_true", help="Start Playwright MCP browser on port 8081")
    parser.add_argument("--nginx", action="store_true", help="Start Nginx reverse proxy")
    parser.add_argument("--all", action="store_true", help="Start app + MCP + Nginx")
    args = parser.parse_args()

    if args.setup:
        try:
            from backend.app.config_loader import config_loader
            if config_loader.exists:
                config_loader.delete()
                print("Configuration reset. Starting setup...")
        except ImportError:
            print("Config loader not found. Starting without setup reset.")

    needs_setup = not check_config()

    port = args.port or 8080
    host = args.host or "0.0.0.0"
    mcp_process = None

    # Handle --all: start everything
    if args.all:
        # Check if nginx is available
        if not check_nginx_installed():
            print("Nginx not found. Install Nginx to use --all. Starting app only.")
            start_server(port=port, host=host)
            return

        # Generate nginx config
        nginx_config = generate_nginx_config(port, 8081)
        config_path = os.path.join(repo_root, "nginx.conf")

        with open(config_path, "w") as f:
            f.write(nginx_config)
        print(f"Nginx config written to {config_path}")

        # Start nginx
        start_nginx(config_path)
        time.sleep(1)

        # Start MCP
        mcp_process = start_playwright_mcp(8081)

        # Start server
        start_server(port=port, host=host)
        return

    # Handle individual flags
    if args.nginx:
        if not check_nginx_installed():
            print("Nginx not found. Install Nginx or add to PATH.")
            return
        nginx_config = generate_nginx_config(port, 8081)
        config_path = os.path.join(repo_root, "nginx.conf")
        with open(config_path, "w") as f:
            f.write(nginx_config)
        start_nginx(config_path)

    if args.mcp:
        start_playwright_mcp(port=8081)

    if args.nginx or args.mcp:
        # Start server after MCP/nginx
        start_server(port=port, host=host)
        return

    # Default: just start server
    needs_setup = not check_config()

    if needs_setup:
        print("First-time setup required.")
        print(f"Open http://localhost:{port}/setup in your browser to configure HomeGallery.")

        if not args.no_browser:
            def open_browser():
                time.sleep(2)
                try:
                    import webbrowser
                    webbrowser.open(f"http://localhost:{port}/setup")
                except Exception:
                    pass

            threading.Thread(target=open_browser, daemon=True).start()

    start_server(port=port, host=host)


if __name__ == "__main__":
    main()
