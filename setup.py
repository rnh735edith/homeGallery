#!/usr/bin/env python
"""
HomeGallery Setup CLI

Usage:
    python setup.py              # Run setup wizard
    python setup.py --force    # Force re-setup (deletes existing config)
    python setup.py --status   # Check if configured
    python setup.py --nginx    # Generate Nginx config
    python setup.py --ssl      # Generate self-signed SSL certs
"""

import argparse
import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def show_status():
    from backend.app.config_loader import config_loader
    if config_loader.exists:
        config = config_loader.load()
        print("Configuration: EXISTS")
        print(f"  Path: {config_loader.config_path}")
        print(f"  Port: {config.get('server', {}).get('port', 8080)}")
        print(f"  Database: {config.get('database', {}).get('type', 'unknown')}")
        print(f"  Admin: {config.get('admin', {}).get('username', 'unknown')}")
    else:
        print("Configuration: NOT FOUND")
        print("Run: python setup.py to configure")


def force_setup():
    from backend.app.config_loader import config_loader
    if config_loader.exists:
        confirm = input("Existing configuration found. Delete and re-setup? [y/N]: ")
        if confirm.lower() != "y":
            print("Aborted")
            return
        config_loader.delete()
        print("Configuration deleted.")
    run_interactive_setup()


def run_interactive_setup():
    from backend.app.config_loader import config_loader, DEFAULT_CONFIG
    from backend.app.utils.security import hash_password
    from getpass import getpass

    print("=" * 50)
    print("  Welcome to HomeGallery Setup!")
    print("=" * 50)
    print()

    config = {
        "server": {"host": "0.0.0.0", "port": 8080},
        "database": {"type": "sqlite", "url": "sqlite:///./data/gallery.db"},
        "storage": {
            "photo_dir": "./data/photos",
            "thumbnail_dir": "./data/thumbnails",
            "face_encoding_dir": "./data/face_encodings",
        },
        "admin": {"username": "admin"},
        "processing": {
            "thumbnail_sizes": {"small": 200, "medium": 800, "large": 1920},
            "auto_thumbnails": True,
            "face_detection": True,
            "face_processing_max_memory_mb": 512,
            "max_concurrent_tasks": 2,
        },
        "security": {},
    }

    print("1. Photo Library")
    photo_dir = input(f"   Where are your photos stored? [{config['storage']['photo_dir']}]: ")
    if photo_dir:
        config["storage"]["photo_dir"] = photo_dir
    print()

    print("2. Admin Account")
    username = input(f"   Username [{config['admin']['username']}]: ")
    if username:
        config["admin"]["username"] = username

    while True:
        password = getpass("   Password: ")
        if len(password) < 6:
            print("   Password must be at least 6 characters")
            continue
        confirm = getpass("   Confirm Password: ")
        if password != confirm:
            print("   Passwords don't match")
            continue
        break

    config["admin"]["password_hash"] = hash_password(password)
    print()

    print("3. Server")
    port = input(f"   Port [{config['server']['port']}]: ")
    if port:
        config["server"]["port"] = int(port)

    host = input(f"   Host [{config['server']['host']}]: ")
    if host:
        config["server"]["host"] = host
    print()

    print("4. Processing")
    thumbs = input("   Auto-generate thumbnails? [Y/n]: ")
    if thumbs.lower() == "n":
        config["processing"]["auto_thumbnails"] = False

    faces = input("   Run face detection? [Y/n]: ")
    if faces.lower() == "n":
        config["processing"]["face_detection"] = False
    print()

    print("=" * 50)
    print("  Configuration Summary")
    print("=" * 50)
    print(f"  Photo dir:    {config['storage']['photo_dir']}")
    print(f"  Admin:        {config['admin']['username']}")
    print(f"  Port:         {config['server']['port']}")
    print(f"  Database:     {config['database']['type']}")
    auto = "Auto" if config["processing"]["auto_thumbnails"] else "Manual"
    print(f"  Thumbnails:   {auto}")
    face_status = "Enabled" if config["processing"]["face_detection"] else "Disabled"
    print(f"  Faces:        {face_status}")
    print()

    confirm = input("  Save configuration? [Y/n]: ")
    if confirm.lower() == "n":
        print("Aborted")
        return

    del config["admin"]["password_hash"]

    config_path = config_loader.save(config)
    print(f"\n  Configuration saved to {config_path}")
    print("  Start the server with: python start.py")


def generate_nginx_config_cli(app_port=8080, mcp_port=8081):
    repo_root = os.path.dirname(os.path.abspath(__file__))

    # Check if nginx is available
    nginx = "nginx" if os.name != "nt" else "nginx.exe"
    try:
        subprocess.run([nginx, "-v"], capture_output=True, check=True)
    except FileNotFoundError:
        print("Nginx not found. Install Nginx to use --nginx.")
        print("https://nginx.org/en/download.html")
        return False

    print(f"Generating Nginx config for app:{app_port} -> MCP:{mcp_port}")

    nginx_config = f'''worker_processes 1;
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

    # Create required directories
    logs_dir = os.path.join(repo_root, "logs")
    ssl_dir = os.path.join(repo_root, "ssl")
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(ssl_dir, exist_ok=True)

    config_path = os.path.join(repo_root, "nginx.conf")
    with open(config_path, "w") as f:
        f.write(nginx_config)

    print(f"  Nginx config written to: {config_path}")
    print(f"  Logs directory: {logs_dir}")
    print(f"  SSL directory: {ssl_dir}")
    print("\nTo enable HTTPS, run: python setup.py --ssl")
    return True


def generate_ssl_certs():
    repo_root = os.path.dirname(os.path.abspath(__file__))
    ssl_dir = os.path.join(repo_root, "ssl")
    os.makedirs(ssl_dir, exist_ok=True)

    cert_path = os.path.join(ssl_dir, "server.crt")
    key_path = os.path.join(ssl_dir, "server.key")

    print("Generating self-signed SSL certificates...")

    try:
        result = subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:4096",
            "-keyout", key_path, "-out", cert_path,
            "-days", "365", "-nodes", "-subj", "/CN=localhost"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False

        print(f"  Certificate: {cert_path}")
        print(f"  Private key: {key_path}")
        print("\nNote: Browsers will show security warnings. Add exception to access via HTTPS.")
        return True
    except FileNotFoundError:
        print("OpenSSL not found. Install it or add to PATH.")
        return False


def main():
    parser = argparse.ArgumentParser(description="HomeGallery Setup CLI")
    parser.add_argument("--force", action="store_true", help="Force re-setup")
    parser.add_argument("--status", action="store_true", help="Show configuration status")
    parser.add_argument("--nginx", action="store_true", help="Generate Nginx config")
    parser.add_argument("--ssl", action="store_true", help="Generate SSL certificates")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.force:
        force_setup()
    elif args.nginx:
        generate_nginx_config_cli()
    elif args.ssl:
        generate_ssl_certs()
    else:
        run_interactive_setup()


if __name__ == "__main__":
    main()
