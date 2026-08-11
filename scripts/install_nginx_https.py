#!/usr/bin/env python3
"""Install Nginx + certbot and issue HTTPS cert for deepopen.com."""
from __future__ import annotations

import os
import sys
import time
import paramiko

HOST = os.environ.get("DEPLOY_HOST", "47.110.251.53")
USER = os.environ.get("DEPLOY_USER", "root")
PASSWORD = os.environ.get("DEPLOY_SSH_PASSWORD", "Deep001open")
REMOTE_DIR = "/opt/ai-manju"
DOMAIN = "deepopen.com"
WWW_DOMAIN = "www.deepopen.com"


def run(client, cmd, timeout=120):
    print(f"\n>>> {cmd[:150]}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=False)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.strip()[-3000:])
    if err.strip():
        print(err.strip()[-2000:], file=sys.stderr)
    return code, out, err


def main() -> int:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=30)

    # Step 1: Install Nginx
    print("\n[1/5] 安装 Nginx")
    code, out, err = run(
        client,
        "export DEBIAN_FRONTEND=noninteractive && "
        "apt-get update -qq && "
        "apt-get install -y -qq nginx",
        timeout=300,
    )
    if code != 0:
        print("❌ Nginx 安装失败", file=sys.stderr)
        return 1

    # Step 2: Install certbot
    print("\n[2/5] 安装 certbot")
    run(
        client,
        "export DEBIAN_FRONTEND=noninteractive && "
        "apt-get install -y -qq certbot python3-certbot-nginx",
        timeout=300,
    )

    # Step 3: Copy Nginx config
    print("\n[3/5] 部署 Nginx 配置")
    run(client, f"cp {REMOTE_DIR}/deploy/nginx/deepopen.conf /etc/nginx/sites-available/deepopen.conf")
    run(client, "rm -f /etc/nginx/sites-enabled/default")
    run(client, "ln -sf /etc/nginx/sites-available/deepopen.conf /etc/nginx/sites-enabled/deepopen.conf")

    # Test config
    code, out, err = run(client, "nginx -t")
    if code != 0:
        print(f"❌ Nginx 配置错误: {out}\n{err}", file=sys.stderr)
        return 1

    # Start Nginx (on port 80 first for certbot)
    run(client, "systemctl enable --now nginx")

    # Step 4: Issue HTTPS cert
    print("\n[4/5] 签发 Let's Encrypt HTTPS 证书")
    code, out, err = run(
        client,
        f"certbot --nginx -d {DOMAIN} -d {WWW_DOMAIN} "
        f"--non-interactive --agree-tos --register-unsafely-without-email "
        f"--redirect",
        timeout=120,
    )
    if code != 0:
        print(f"⚠️  certbot 签发失败: {out[:500]} {err[:500]}", file=sys.stderr)
        print("   可能 DNS 尚未完全生效，稍后手动执行: certbot --nginx -d {DOMAIN} -d {WWW_DOMAIN}")
    else:
        print("  ✅ HTTPS 证书签发成功")

    # Step 5: Verify
    print("\n[5/5] 验证")
    time.sleep(2)
    code, out, _ = run(client, f"curl -sfI https://{DOMAIN}/ | head -5", timeout=15)
    code2, out2, _ = run(client, f"curl -sfI https://{DOMAIN}/api/v1/health | head -5", timeout=15)
    code3, out3, _ = run(client, f"curl -sfI http://127.0.0.1/ | head -5", timeout=10)

    # Show Nginx status
    run(client, "systemctl status nginx --no-pager | head -5", timeout=10)
    run(client, f"ls /etc/letsencrypt/live/{DOMAIN}/ 2>&1", timeout=10)

    client.close()
    print(f"\n🎉 Nginx + HTTPS 部署完成！访问 https://{DOMAIN}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
