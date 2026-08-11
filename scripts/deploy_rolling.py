#!/usr/bin/env python3
"""Rolling deploy: pull + restart api/web only (no DB reset)."""
from __future__ import annotations

import os
import sys
import time

import paramiko

HOST = os.environ.get("DEPLOY_HOST", "47.89.247.240")
USER = os.environ.get("DEPLOY_USER", "root")
PASSWORD = os.environ.get("DEPLOY_SSH_PASSWORD", "Gcc20260717")
REMOTE_DIR = "/opt/ai-manju"


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 600) -> tuple[int, str, str]:
    print(f"\n>>> {cmd}")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    if out:
        print(out, end="" if out.endswith("\n") else "\n")
    if err:
        print(err, end="" if err.endswith("\n") else "\n", file=sys.stderr)
    return code, out, err


def main() -> int:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting {USER}@{HOST} ...")
    client.connect(HOST, username=USER, password=PASSWORD, timeout=30)

    run(
        client,
        "echo 'pQ865tsPZHefe6txNa5V' | docker login gcc-registry.cn-hangzhou.cr.aliyuncs.com "
        "-u 'yi@1598957496698065' --password-stdin",
    )

    code, _, _ = run(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml pull api web")
    if code != 0:
        return 1

    code, _, _ = run(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml up -d api web")
    if code != 0:
        return 1

    for _ in range(40):
        _, out, _ = run(client, "curl -sf http://127.0.0.1:7051/api/v1/health || true")
        if "UP" in out:
            break
        time.sleep(3)
    else:
        print("API health check failed", file=sys.stderr)
        run(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml logs --tail=80 api")
        return 1

    run(client, "curl -sfI https://www.printfilm.com/api/v1/health | head -8")
    run(client, "curl -sfI https://www.printfilm.com/ | head -8")
    run(
        client,
        "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'printfilm|NAMES'",
    )
    client.close()
    print("\nDeploy finished: https://www.printfilm.com/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
