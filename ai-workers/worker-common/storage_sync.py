import os
import subprocess
from pathlib import Path


def sync_image(local_path, storage_key):
    """Chuyển ảnh sang VM4 trước khi đánh dấu job DONE."""
    target = os.getenv("STORAGE_SSH_TARGET")
    remote_dir = os.getenv("STORAGE_REMOTE_DIR", "/var/lib/bt03/images")

    if not target:
        raise RuntimeError("Chưa cấu hình STORAGE_SSH_TARGET")

    key = Path(storage_key)
    if key.is_absolute() or ".." in key.parts:
        raise ValueError("storage_key không hợp lệ")

    destination = remote_dir.rstrip("/") + "/" + key.as_posix()
    parent = str(Path(destination).parent)

    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
    subprocess.run(
        ssh + [target, "mkdir -p -- " + __import__("shlex").quote(parent)],
        check=True, timeout=20
    )

    subprocess.run(
        ["rsync", "-az", "--protect-args", "-e",
         "ssh -o BatchMode=yes -o ConnectTimeout=10",
         str(local_path), f"{target}:{destination}"],
        check=True, timeout=120
    )


def verify_remote_image(storage_key):
    """Kiểm tra file ảnh tồn tại trên VM4."""
    import shlex

    target = os.getenv("STORAGE_SSH_TARGET")
    remote_dir = os.getenv("STORAGE_REMOTE_DIR", "/var/lib/bt03/images")

    if not target:
        raise RuntimeError("Chưa cấu hình STORAGE_SSH_TARGET")

    key = Path(storage_key)
    if key.is_absolute() or ".." in key.parts:
        raise ValueError("storage_key không hợp lệ")

    remote_path = remote_dir.rstrip("/") + "/" + key.as_posix()
    subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
         target, "test -s -- " + shlex.quote(remote_path)],
        check=True, timeout=20
    )
