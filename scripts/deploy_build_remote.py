#!/usr/bin/env python3
"""Build api/web on the production host and rolling-restart (no local Docker required).

可复用部署脚本，完整流程：
  1. 本地打包源码（排除 node_modules/.git/target/.next/data/tmp-* 等）
  2. SFTP 上传到服务器 /tmp/ai-manju-src.tar.gz，解压到 /opt/ai-manju-build
  3. 复用服务器现有 .env.prod，同步 docker-compose.prod.yml 与 nginx 配置
  4. ACR 登录
  5. 服务器上 docker buildx build（禁用 attestation，单平台 linux/amd64，--load）
  6. docker push 到 ACR（失败则容错继续，用本地镜像）
  7. docker compose -f docker-compose.prod.yml up -d --force-recreate api web
  8. 轮询健康检查 + 公网 HTTPS 验证 + 容器/镜像状态报告

不碰数据库（postgres/redis 不重启）。

用法:
  python scripts/deploy_build_remote.py                     # 默认部署到 47.89.247.240
  python scripts/deploy_build_remote.py --image-tag v1.2    # 指定镜像 tag
  python scripts/deploy_build_remote.py --skip-upload       # 复用上次上传的源码
  python scripts/deploy_build_remote.py --skip-push         # 只构建+重启，不推 ACR
  DEPLOY_SSH_PASSWORD=xxx python scripts/deploy_build_remote.py --host 1.2.3.4

敏感参数优先读环境变量：DEPLOY_HOST / DEPLOY_USER / DEPLOY_SSH_PASSWORD /
ACR_USER / ACR_PASSWORD / IMAGE_TAG。命令行参数可覆盖环境变量。
"""
from __future__ import annotations

import argparse
import os
import sys
import tarfile
import tempfile
import time
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
REMOTE_DIR = "/opt/ai-manju"
REMOTE_BUILD = "/opt/ai-manju-build"
REMOTE_TAR = "/tmp/ai-manju-src.tar.gz"

# ACR（阿里云容器镜像服务）
ACR_REGISTRY = "gcc-registry.cn-hangzhou.cr.aliyuncs.com"
ACR_NAMESPACE = "gcc"
ACR_USER_DEFAULT = "yi@1598957496698065"
ACR_PASSWORD_DEFAULT = "pQ865tsPZHefe6txNa5V"

API_IMAGE = f"{ACR_REGISTRY}/{ACR_NAMESPACE}/ai-manju-api"
WEB_IMAGE = f"{ACR_REGISTRY}/{ACR_NAMESPACE}/ai-manju-web"

# 构建配置（与 docker-compose.full.yml 的 build 段保持一致）
# 改动 compose 的 build 段时，这里需同步。
BUILDS = [
    {
        "name": "api",
        "image": API_IMAGE,
        "context": "services/api",
        "dockerfile": "services/api/Dockerfile",
        "args": [],
    },
    {
        "name": "web",
        "image": WEB_IMAGE,
        "context": ".",
        "dockerfile": "apps/web/Dockerfile",
        "args": ["NEXT_PUBLIC_API_URL=http://localhost:7051"],
    },
]

EXCLUDE_DIR_NAMES = {
    ".git",
    "node_modules",
    ".next",
    "target",
    "dist",
    "build",
    "data",
    ".idea",
    ".vscode",
    "__pycache__",
    ".cursor",
    "agent-transcripts",
    "agent-tools",
}
EXCLUDE_FILE_SUFFIXES = (".dump", ".log", ".iml", ".tsbuildinfo")
EXCLUDE_FILE_NAMES = {"printfilm.dump", ".DS_Store", "Thumbs.db", "tmp-source.tar.gz"}


def should_exclude(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if set(rel.parts) & EXCLUDE_DIR_NAMES:
        return True
    if path.name in EXCLUDE_FILE_NAMES:
        return True
    if path.name.startswith("._"):
        return True
    if path.name.startswith("tmp-"):  # 本地临时文件/日志，不入包
        return True
    if path.suffix in EXCLUDE_FILE_SUFFIXES:
        return True
    if rel.as_posix().startswith("scripts/_deploy_"):
        return True
    return False


def make_tarball(dest: Path) -> None:
    print(f"[1/8] 打包源码 -> {dest.name}")
    count = 0
    with tarfile.open(dest, "w:gz") as tar:
        for path in ROOT.rglob("*"):
            if not path.is_file() or should_exclude(path):
                continue
            tar.add(path, arcname=path.relative_to(ROOT).as_posix())
            count += 1
    print(f"      打包 {count} 个文件, {dest.stat().st_size / 1e6:.1f} MB")


def _safe_write(text: str, *, file=sys.stdout) -> None:
    try:
        file.write(text)
        file.flush()
    except UnicodeEncodeError:
        enc = getattr(file, "encoding", None) or "utf-8"
        file.buffer.write(text.encode(enc, errors="replace"))
        file.flush()


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 3600, quiet: bool = False) -> tuple[int, str]:
    """执行远端命令，实时回显输出。quiet=True 时只抑制 '>>> cmd' 前缀。"""
    if not quiet:
        print(f"\n>>> {cmd}", flush=True)
    # No PTY: more reliable for long docker builds / background jobs.
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=False)
    channel = stdout.channel
    out_chunks: list[str] = []
    while True:
        if channel.recv_ready():
            chunk = channel.recv(65536).decode(errors="replace")
            out_chunks.append(chunk)
            _safe_write(chunk)
        if channel.recv_stderr_ready():
            chunk = channel.recv_stderr(65536).decode(errors="replace")
            out_chunks.append(chunk)
            _safe_write(chunk, file=sys.stderr)
        if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
            break
        time.sleep(0.05)
    return channel.recv_exit_status(), "".join(out_chunks)


def connect(host: str, user: str, password: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"连接 {user}@{host} ...", flush=True)
    client.connect(host, username=user, password=password, timeout=30)
    return client


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(description="远程构建并部署 Printfilm (ai-manju)")
    parser.add_argument("--host", default=os.environ.get("DEPLOY_HOST", "47.89.247.240"))
    parser.add_argument("--user", default=os.environ.get("DEPLOY_USER", "root"))
    parser.add_argument("--password", default=os.environ.get("DEPLOY_SSH_PASSWORD", "Gcc20260717"))
    parser.add_argument("--image-tag", default=os.environ.get("IMAGE_TAG", "latest"))
    parser.add_argument("--remote-dir", default=REMOTE_DIR)
    parser.add_argument("--skip-upload", action="store_true", help="复用服务器上上次上传的源码")
    parser.add_argument("--skip-push", action="store_true", help="只构建+重启，不推 ACR")
    args = parser.parse_args()

    tag = args.image_tag
    acr_user = os.environ.get("ACR_USER", ACR_USER_DEFAULT)
    acr_pwd = os.environ.get("ACR_PASSWORD", ACR_PASSWORD_DEFAULT)

    client = connect(args.host, args.user, args.password)

    code, _ = run(client, "df -h / | tail -1", timeout=30, quiet=True)
    if code != 0:
        return 1

    # 1-2. 打包 + 上传 + 解压
    if not args.skip_upload:
        with tempfile.TemporaryDirectory() as tmp:
            tar_path = Path(tmp) / "ai-manju-src.tar.gz"
            make_tarball(tar_path)
            print(f"[2/8] 上传 -> {REMOTE_TAR}", flush=True)
            sftp = client.open_sftp()
            sftp.put(str(tar_path), REMOTE_TAR)
            sftp.close()

        code, _ = run(
            client,
            f"rm -rf {REMOTE_BUILD} && mkdir -p {REMOTE_BUILD} && "
            f"tar -xzf {REMOTE_TAR} -C {REMOTE_BUILD} && "
            f"cp -f {args.remote_dir}/.env.prod {REMOTE_BUILD}/.env.prod 2>/dev/null || true && "
            f"cp -f {REMOTE_BUILD}/docker-compose.prod.yml {args.remote_dir}/docker-compose.prod.yml && "
            f"mkdir -p {args.remote_dir}/deploy/nginx && "
            f"cp -f {REMOTE_BUILD}/deploy/nginx/printfilm.conf "
            f"{args.remote_dir}/deploy/nginx/printfilm.conf 2>/dev/null || true",
            timeout=120,
        )
        if code != 0:
            return 1
    else:
        print("[1-2/8] SKIP_UPLOAD，复用服务器上 " + REMOTE_BUILD)

    # 3. ACR 登录
    print(f"[3/8] ACR 登录 {ACR_REGISTRY}", flush=True)
    run(
        client,
        f"echo '{acr_pwd}' | docker login {ACR_REGISTRY} -u '{acr_user}' --password-stdin",
        timeout=60,
        quiet=True,
    )

    # 4. 构建（优先使用 buildx，无 buildx 时回退到 DOCKER_BUILDKIT=0）
    print(f"[4/8] 远程构建 api/web（tag={tag}）...", flush=True)
    # 检测 buildx 是否可用
    code, out = run(client, "docker buildx version 2>/dev/null || echo 'NO_BUILDX'", timeout=10, quiet=True)
    has_buildx = "NO_BUILDX" not in out
    if has_buildx:
        print("      使用 docker buildx（支持 provenance/sbom 禁用）", flush=True)
    else:
        print("      使用 DOCKER_BUILDKIT=0 docker build（无 buildx，已禁用 BuildKit 避免 attestation）", flush=True)

    for b in BUILDS:
        full_tag = f"{b['image']}:{tag}"
        arg_flags = " ".join(f"--build-arg {a}" for a in b["args"])
        if has_buildx:
            cmd = (
                f"cd {REMOTE_BUILD} && docker buildx build "
                f"--provenance=false --sbom=false --platform linux/amd64 --load "
                f"-t {full_tag} -f {b['dockerfile']} {arg_flags} {b['context']}"
            )
        else:
            cmd = (
                f"cd {REMOTE_BUILD} && DOCKER_BUILDKIT=0 docker build "
                f"-t {full_tag} -f {b['dockerfile']} {arg_flags} {b['context']}"
            )
        code, _ = run(client, cmd, timeout=3600)
        if code != 0:
            print(f"构建失败: {b['name']}", file=sys.stderr)
            return 1
        print(f"      ✓ {b['name']} -> {full_tag}")

    # 5. 推送 ACR（容错：失败仍继续 force-recreate，用本地镜像）
    if args.skip_push:
        print("[5/8] SKIP_PUSH，跳过 ACR 推送")
    else:
        print(f"[5/8] 推送 ACR（tag={tag}）...", flush=True)
        push_failed = False
        for b in BUILDS:
            full_tag = f"{b['image']}:{tag}"
            code, _ = run(client, f"docker push {full_tag}", timeout=1800, quiet=True)
            if code != 0:
                print(f"      ✗ push 失败: {full_tag}（将用本地镜像继续）", file=sys.stderr)
                push_failed = True
            else:
                print(f"      ✓ pushed {full_tag}")
        if push_failed:
            print("      部分 push 失败，继续用本地镜像 force-recreate", file=sys.stderr)

    # 长推送后 SSH 可能已断，重建连接再滚动重启
    try:
        client.get_transport().send_ignore()
    except Exception:
        print("SSH stale after push, reconnecting ...", flush=True)
        try:
            client.close()
        except Exception:
            pass
        client = connect(args.host, args.user, args.password)

    # 6. force-recreate api/web（显式传 IMAGE_TAG，保证与构建 tag 一致）
    print(f"[6/8] force-recreate api/web（tag={tag}）...", flush=True)
    code, _ = run(
        client,
        f"cd {args.remote_dir} && IMAGE_TAG={tag} docker-compose -f docker-compose.prod.yml "
	    f"up -d --force-recreate api web",
        timeout=600,
    )
    if code != 0:
        return 1

    # 7. 健康检查（轮询）
    print("[7/8] 健康检查...", flush=True)
    for _ in range(40):
        _, out = run(client, "curl -sf http://127.0.0.1:7051/api/v1/health || true", timeout=30, quiet=True)
        if "UP" in out:
            print("      ✓ API UP")
            break
        time.sleep(3)
    else:
        print("API health check failed", file=sys.stderr)
        run(client, f"cd {args.remote_dir} && docker-compose -f docker-compose.prod.yml logs --tail=80 api", timeout=60)
        return 1

    # 8. 部署后验证报告
    print("[8/8] 部署后验证", flush=True)
    print("  -- 公网 HTTPS API --", flush=True)
    run(client, "curl -sfI https://www.printfilm.com/api/v1/health | head -3", timeout=30, quiet=True)
    print("  -- 公网 HTTPS Web --", flush=True)
    run(client, "curl -sfI https://www.printfilm.com/ | head -3", timeout=30, quiet=True)
    print("  -- 容器状态 --", flush=True)
    run(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.RunningFor}}' | grep -E 'printfilm|NAMES'", timeout=30, quiet=True)
    print("  -- api 镜像 --", flush=True)
    # 注意：docker --format 的 {{}} 在普通字符串里原样传递
    run(client, "docker inspect printfilm-api --format '{{.Config.Image}} created={{.Created}}'", timeout=30, quiet=True)

    run(client, f"rm -f {REMOTE_TAR}", timeout=30, quiet=True)
    client.close()
    print(f"\n✅ 部署完成: https://www.printfilm.com/  (tag={tag})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
