#!/usr/bin/env python3
"""
Universal FTP deploy script for REG.ru hosting.
Usage:
    python3 ftp-deploy.py \
        --host <ftp_host> --user <ftp_user> --password <pwd> \
        --local-dir <dist_path> --remote-dir <remote_path> \
        [--clean-assets] [--skip-media] [--dry-run] [--timeout 30]
"""

import argparse
import ftplib
import json
import os
import sys
import time


MEDIA_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.mp3', '.wav', '.flac'}
SKIP_SIZE_MB = 50  # skip media files larger than this


def punycode_host(host: str) -> str:
    """Convert internationalized domain to punycode if needed."""
    try:
        return host.encode('idna').decode('ascii')
    except (UnicodeError, UnicodeDecodeError):
        return host


def connect_ftp(host: str, user: str, password: str, timeout: int) -> ftplib.FTP:
    """Connect to FTP server with retry logic."""
    host = punycode_host(host)
    last_err = None
    for attempt in range(1, 4):
        try:
            ftp = ftplib.FTP(timeout=timeout)
            ftp.connect(host, 21)
            ftp.login(user, password)
            ftp.encoding = 'utf-8'
            print(f"[OK] Connected to {host} as {user}")
            return ftp
        except Exception as e:
            last_err = e
            print(f"[RETRY {attempt}/3] Connection failed: {e}")
            time.sleep(2 * attempt)
    print(f"[FAIL] Could not connect after 3 attempts: {last_err}")
    sys.exit(1)


def ensure_remote_dir(ftp: ftplib.FTP, path: str):
    """Create remote directory tree if it doesn't exist."""
    dirs = path.strip('/').split('/')
    current = ''
    for d in dirs:
        current += f'/{d}'
        try:
            ftp.cwd(current)
        except ftplib.error_perm:
            try:
                ftp.mkd(current)
            except ftplib.error_perm:
                pass


def list_remote(ftp: ftplib.FTP, path: str) -> list:
    """List files/dirs in remote path."""
    try:
        return ftp.nlst(path)
    except ftplib.error_perm:
        return []


def remove_remote_dir(ftp: ftplib.FTP, path: str):
    """Recursively remove a remote directory."""
    items = list_remote(ftp, path)
    for item in items:
        if item in ('.', '..'):
            continue
        full = f"{path}/{item}" if not item.startswith('/') else item
        # skip . and .. entries
        basename = os.path.basename(full)
        if basename in ('.', '..'):
            continue
        try:
            ftp.delete(full)
        except ftplib.error_perm:
            # it's a directory
            remove_remote_dir(ftp, full)
    try:
        ftp.rmd(path)
    except ftplib.error_perm:
        pass


def clean_remote_assets(ftp: ftplib.FTP, remote_dir: str, dry_run: bool = False):
    """Remove assets/ directory on remote to avoid stale hashed files."""
    assets_path = f"{remote_dir}/assets"
    items = list_remote(ftp, assets_path)
    if not items:
        print(f"[SKIP] No remote assets/ to clean")
        return
    if dry_run:
        print(f"[DRY-RUN] Would clean {assets_path}")
        return
    print(f"[CLEAN] Removing {assets_path}...")
    remove_remote_dir(ftp, assets_path)
    print(f"[OK] Remote assets/ cleaned")


def should_skip_file(filepath: str, skip_media: bool) -> bool:
    """Check if file should be skipped based on extension and size."""
    if not skip_media:
        return False
    ext = os.path.splitext(filepath)[1].lower()
    if ext in MEDIA_EXTENSIONS:
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if size_mb > SKIP_SIZE_MB:
            return True
    return False


def upload_dir(ftp: ftplib.FTP, local_dir: str, remote_dir: str,
               skip_media: bool = False, dry_run: bool = False) -> dict:
    """Recursively upload a local directory to remote FTP."""
    stats = {'uploaded': 0, 'skipped': 0, 'bytes': 0, 'errors': 0}

    if not os.path.isdir(local_dir):
        print(f"[ERROR] Local directory not found: {local_dir}")
        sys.exit(1)

    for root, dirs, files in os.walk(local_dir):
        # compute relative path
        rel_path = os.path.relpath(root, local_dir)
        if rel_path == '.':
            remote_path = remote_dir
        else:
            remote_path = f"{remote_dir}/{rel_path}"

        if not dry_run:
            ensure_remote_dir(ftp, remote_path)

        for fname in files:
            local_file = os.path.join(root, fname)
            remote_file = f"{remote_path}/{fname}"

            if should_skip_file(local_file, skip_media):
                size_mb = os.path.getsize(local_file) / (1024 * 1024)
                print(f"[SKIP] {fname} ({size_mb:.1f} MB)")
                stats['skipped'] += 1
                continue

            file_size = os.path.getsize(local_file)

            if dry_run:
                print(f"[DRY-RUN] Would upload {local_file} → {remote_file} ({file_size} bytes)")
                stats['uploaded'] += 1
                stats['bytes'] += file_size
                continue

            try:
                with open(local_file, 'rb') as f:
                    ftp.storbinary(f'STOR {remote_file}', f)
                stats['uploaded'] += 1
                stats['bytes'] += file_size
                print(f"[OK] {remote_file} ({file_size} bytes)")
            except Exception as e:
                print(f"[ERROR] {remote_file}: {e}")
                stats['errors'] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description='Universal FTP deploy for REG.ru')
    parser.add_argument('--host', required=True, help='FTP host')
    parser.add_argument('--user', required=True, help='FTP username')
    parser.add_argument('--password', required=True, help='FTP password')
    parser.add_argument('--local-dir', required=True, help='Local directory to upload')
    parser.add_argument('--remote-dir', required=True, help='Remote directory path')
    parser.add_argument('--clean-assets', action='store_true', help='Remove remote assets/ before upload')
    parser.add_argument('--skip-media', action='store_true', help='Skip large media files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without uploading')
    parser.add_argument('--timeout', type=int, default=30, help='FTP connection timeout in seconds')
    args = parser.parse_args()

    start = time.time()

    ftp = connect_ftp(args.host, args.user, args.password, args.timeout)

    try:
        if args.clean_assets:
            clean_remote_assets(ftp, args.remote_dir, args.dry_run)

        stats = upload_dir(ftp, args.local_dir, args.remote_dir,
                          skip_media=args.skip_media, dry_run=args.dry_run)
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()

    elapsed = round(time.time() - start, 2)
    stats['elapsed'] = elapsed

    print(f"\n{'=' * 40}")
    print(json.dumps(stats, indent=2))
    print(f"{'=' * 40}")

    if stats.get('errors', 0) > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
