"""把中文 BM25 补丁打进运行中的 mem0 容器（不 restart，热重载）。

步骤：备份原文件 → pip install jieba → docker cp 覆盖 →
touch /app/main.py 触发 uvicorn StatReload → 验证分词。

注意：必须在 baseline 跑完之后执行，否则会污染基线结果。
容器重启会重装 PyPI 版 mem0 冲掉补丁，重启后需重新执行本脚本。
"""
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
CONTAINER = "mem0-dev-mem0-1"
TARGET = "/usr/local/lib/python3.12/site-packages/mem0/utils/lemmatization.py"
BACKUP = ROOT / "optimization" / "lemmatization_original_backup.py"
PATCH = ROOT / "optimization" / "lemmatization_zh.py"


def run(*args):
    print("+", " ".join(args))
    subprocess.run(args, check=True)


def main():
    if not BACKUP.exists():
        run("docker", "cp", f"{CONTAINER}:{TARGET}", str(BACKUP))
        print(f"原文件已备份到 {BACKUP}")
    run("docker", "exec", CONTAINER, "pip", "install", "-q", "jieba")
    run("docker", "cp", str(PATCH), f"{CONTAINER}:{TARGET}")
    run("docker", "exec", CONTAINER, "touch", "/app/main.py")
    print("等待 uvicorn 重载...")
    time.sleep(5)
    out = subprocess.run(
        ["docker", "exec", CONTAINER, "python", "-c",
         "from mem0.utils.lemmatization import lemmatize_for_bm25; "
         "print(lemmatize_for_bm25('李承泽对什么过敏？他喝奶茶要换燕麦奶'))"],
        capture_output=True, text=True, encoding="utf-8", check=True)
    print("分词验证:", out.stdout.strip())
    if "过敏" not in out.stdout:
        raise SystemExit("验证失败：输出中没有独立词元，补丁可能未生效")
    print("补丁已生效。接下来跑: py eval/run_eval.py --tag optimized")


if __name__ == "__main__":
    main()