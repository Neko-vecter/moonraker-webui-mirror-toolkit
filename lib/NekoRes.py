import logging
import tempfile
import os
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

class NekoRes:
    def __init__(self, api_url):
        self.api_url = api_url

    def get_releases(self):
        r = requests.get(self.api_url, timeout=10)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def download_file(remote_url: str, dst_file: Path, remote_size: int, remote_ts: float) -> bool:
        try:
            if dst_file.is_file():
                stat = dst_file.stat()
                if stat.st_size == remote_size and stat.st_mtime == remote_ts:
                    logger.info(f"Skipping {dst_file.name}, up to date.")
                    return True

            dst_file.parent.mkdir(parents=True, exist_ok=True)
            
            with requests.get(remote_url, stream=True, timeout=(7, 10)) as r:
                r.raise_for_status()
                tmp_dst = None
                try:
                    with tempfile.NamedTemporaryFile(
                        prefix=f".{dst_file.name}.", suffix=".tmp",
                        dir=dst_file.parent, delete=False
                    ) as f:
                        tmp_dst = Path(f.name)
                        for chunk in r.iter_content(chunk_size=1 << 20):
                            if chunk: f.write(chunk)
                    
                    if remote_size != -1 and tmp_dst.stat().st_size != remote_size:
                        raise Exception(f"Size mismatch for {dst_file.name}")

                    os.utime(tmp_dst, (remote_ts, remote_ts))
                    tmp_dst.chmod(0o644)
                    tmp_dst.replace(dst_file)
                    logger.info(f"Downloaded: {dst_file.name}")
                    return True
                finally:
                    if tmp_dst and tmp_dst.exists(): tmp_dst.unlink()
        except Exception as e:
            logger.error(f"Failed to download {dst_file.name}: {e}")
            return False

    @staticmethod
    def ensure_safe_name(filename: str) -> str:
        filename = filename.replace("\0", " ")
        if filename == ".":
            return " ."
        elif filename == "..":
            return ". ."
        else:
            return filename.replace("/", "_").replace("\\", "_")
