#!/usr/bin/env python3
"""Rename printfilm / printfilm → printfilm across the repo."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "target",
    "data",
    ".idea",
    "dist",
    "build",
}

# Longer / more specific first
TEXT_REPLACEMENTS = [
    ("@printfilm/shared-types", "@printfilm/shared-types"),
    ("@printfilm/web", "@printfilm/web"),
    ("printfilm-postgres", "printfilm-postgres"),
    ("printfilm-redis", "printfilm-redis"),
    ("printfilm-api", "printfilm-api"),
    ("printfilm-dev-secret-key-change-in-production-32b", "printfilm-dev-secret-key-change-in-production-32b"),
    ("admin@printfilm.local", "admin@printfilm.local"),
    ("com.printfilm", "com.printfilm"),
    ("printfilm_dev", "printfilm_dev"),
    ("printfilm", "printfilm"),
    ("printfilm", "printfilm"),
    ("printfilm", "printfilm"),
    ("Printfilm", "Printfilm"),
]


def should_skip(path: Path) -> bool:
    return bool(set(path.parts) & SKIP_DIRS)


def replace_text(text: str) -> str:
    for old, new in TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def process_files() -> int:
    n = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue
        if path.suffix.lower() in {
            ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
            ".jar", ".class", ".mp3", ".mp4", ".woff", ".woff2", ".lock",
        }:
            # still process package-lock via separate npm install
            if path.name != "package-lock.json":
                continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:1024]:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        new_text = replace_text(text)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8", newline="\n")
            n += 1
            print("file:", path.relative_to(ROOT))
    return n


def rename_java_packages() -> None:
    pairs = [
        (
            ROOT / "services/api/src/main/java/com/printfilm",
            ROOT / "services/api/src/main/java/com/printfilm",
        ),
        (
            ROOT / "services/api/src/test/java/com/printfilm",
            ROOT / "services/api/src/test/java/com/printfilm",
        ),
    ]
    for src, dst in pairs:
        if not src.exists():
            print("skip missing", src)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            raise SystemExit(f"dest exists: {dst}")
        src.rename(dst)
        print("dir:", src.relative_to(ROOT), "->", dst.relative_to(ROOT))
        # cleanup empty com/printfilm parents if empty
        parent = src.parent
        while parent != ROOT and parent.name in {"printfilm", "com"} and parent.exists():
            try:
                parent.rmdir()
                parent = parent.parent
            except OSError:
                break


def main() -> None:
    print("updating file contents...")
    n = process_files()
    print(f"updated_files={n}")
    print("renaming java packages...")
    rename_java_packages()
    print("done")


if __name__ == "__main__":
    main()
