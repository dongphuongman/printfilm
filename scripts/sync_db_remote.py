#!/usr/bin/env python3
"""仅同步本地 printfilm.dump 到生产 Postgres（不重建容器栈）。"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
HOST = sys.argv[1] if len(sys.argv) > 1 else "47.89.247.240"
USER = sys.argv[2] if len(sys.argv) > 2 else "root"
PASSWORD = sys.argv[3] if len(sys.argv) > 3 else "Gcc20260717"
REMOTE_DIR = "/opt/ai-manju"
DUMP_LOCAL = ROOT / "printfilm.dump"


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
    if not DUMP_LOCAL.exists():
        print(f"Missing dump: {DUMP_LOCAL}", file=sys.stderr)
        print("Run: docker exec printfilm-postgres pg_dump -U printfilm -Fc printfilm -f /tmp/printfilm.dump")
        print("     docker cp printfilm-postgres:/tmp/printfilm.dump ./printfilm.dump")
        return 1

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting {USER}@{HOST} ...")
    client.connect(HOST, username=USER, password=PASSWORD, timeout=30)

    sftp = client.open_sftp()
    print(f"upload {DUMP_LOCAL.name} -> {REMOTE_DIR}/printfilm.dump")
    sftp.put(str(DUMP_LOCAL), f"{REMOTE_DIR}/printfilm.dump")
    sftp.close()

    for _ in range(30):
        _, out, _ = run(client, "docker inspect printfilm-postgres --format '{{.State.Health.Status}}'")
        if "healthy" in out:
            break
        time.sleep(2)
    else:
        print("Postgres not healthy", file=sys.stderr)
        return 1

    run(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml stop api web")
    run(
        client,
        f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml exec -T postgres "
        "psql -U printfilm -d postgres -c "
        "\"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname='printfilm' AND pid <> pg_backend_pid();\" "
        "-c 'DROP DATABASE IF EXISTS printfilm;' "
        "-c 'CREATE DATABASE printfilm OWNER printfilm;'",
    )
    code, _, _ = run(
        client,
        f"cd {REMOTE_DIR} && cat printfilm.dump | docker compose -f docker-compose.prod.yml exec -T postgres "
        "pg_restore -U printfilm -d printfilm --no-owner --no-privileges --clean --if-exists 2>&1 | tail -20",
        timeout=300,
    )
    run(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml pull api web")
    run(client, f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml up -d api web")
    run(client, "curl -sf http://127.0.0.1:7051/api/v1/health")

    client.close()
    print("\nDatabase sync finished.")
    return 0 if code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
