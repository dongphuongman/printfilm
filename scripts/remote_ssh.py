#!/usr/bin/env python3
"""Run remote commands via SSH (paramiko)."""
import sys
import paramiko

HOST = sys.argv[1] if len(sys.argv) > 1 else "47.89.247.240"
USER = sys.argv[2] if len(sys.argv) > 2 else "root"
PASSWORD = sys.argv[3] if len(sys.argv) > 3 else "Gcc20260717"
CMD = sys.argv[4] if len(sys.argv) > 4 else "docker ps -a"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
_, stdout, stderr = client.exec_command(CMD, timeout=300)
out = stdout.read().decode()
err = stderr.read().decode()
if out:
    print(out, end="")
if err:
    print(err, end="", file=sys.stderr)
client.close()
sys.exit(0 if not err else 1)
