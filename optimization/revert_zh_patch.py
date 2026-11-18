"""还原 mem0 原版 lemmatization（对照/回滚用）。"""
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
CONTAINER = "mem0-dev-mem0-1"
TARGET = "/usr/local/lib/python3.12/site-packages/mem0/utils/lemmatization.py"
BACKUP = ROOT / "optimization" / "lemmatization_original_backup.py"


def main():
    if not BACKUP.exists():
        raise SystemExit("没有备份文件，无法还原")
    subprocess.run(["docker", "cp", str(BACKUP), f"{CONTAINER}:{TARGET}"], check=True)
    pg_backup = ROOT / "optimization" / "pgvector_original_backup.py"
    if pg_backup.exists():
        subprocess.run(["docker", "cp", str(pg_backup),
                        f"{CONTAINER}:/usr/local/lib/python3.12/site-packages/mem0/vector_stores/pgvector.py"],
                       check=True)
    subprocess.run(["docker", "exec", CONTAINER, "touch", "/app/main.py"], check=True)
    time.sleep(5)
    out = subprocess.run(
        ["docker", "exec", CONTAINER, "python", "-c",
         "from mem0.utils.lemmatization import lemmatize_for_bm25; "
         "print(lemmatize_for_bm25(' attending meetings '))"],
        capture_output=True, text=True, encoding="utf-8", check=True)
    print("还原验证:", out.stdout.strip())
    print("已恢复原版。")


if __name__ == "__main__":
    main()