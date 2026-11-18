"""第二阶段补丁：pgvector 关键词检索 AND→OR 语义。

诊断：jieba 分词后 BM25 仍为 0，因为 plainto_tsquery 把查询所有词元
做 AND——自然语言问句（人名+疑问词+关键词）几乎不可能全部命中同一条记忆。
改为 OR（to_tsquery 以 | 连接），ts_rank_cd 仍按命中词元数排序。

在 apply_zh_patch.py 之后执行。同样走热重载，不 restart。
"""
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
CONTAINER = "mem0-dev-mem0-1"
TARGET = "/usr/local/lib/python3.12/site-packages/mem0/vector_stores/pgvector.py"
BACKUP = ROOT / "optimization" / "pgvector_original_backup.py"
WORK = ROOT / "optimization" / "pgvector_or.py"

OLD = """        try:
            with self._get_cursor() as cur:
                cur.execute(
                    sql.SQL(\"\"\"
                    SELECT id, ts_rank_cd(to_tsvector('simple', payload->>'text_lemmatized'), plainto_tsquery('simple', %s)) AS score, payload
                    FROM {}
                    WHERE to_tsvector('simple', payload->>'text_lemmatized') @@ plainto_tsquery('simple', %s)
                    {}
                    ORDER BY score DESC
                    LIMIT %s
                    \"\"\").format(self._col(), filter_clause),
                    (query, query, *filter_params, top_k),
                )"""

NEW = """        tokens = [t for t in query.split() if t]
        tsq = " | ".join("'" + t.replace("'", "''") + "'" for t in tokens) if tokens else query
        try:
            with self._get_cursor() as cur:
                cur.execute(
                    sql.SQL(\"\"\"
                    SELECT id, ts_rank_cd(to_tsvector('simple', payload->>'text_lemmatized'), to_tsquery('simple', %s)) AS score, payload
                    FROM {}
                    WHERE to_tsvector('simple', payload->>'text_lemmatized') @@ to_tsquery('simple', %s)
                    {}
                    ORDER BY score DESC
                    LIMIT %s
                    \"\"\").format(self._col(), filter_clause),
                    (tsq, tsq, *filter_params, top_k),
                )"""


def run(*args):
    print("+", " ".join(args))
    subprocess.run(args, check=True)


def main():
    if not BACKUP.exists():
        run("docker", "cp", f"{CONTAINER}:{TARGET}", str(BACKUP))
    text = BACKUP.read_text(encoding="utf-8")
    if OLD not in text:
        raise SystemExit("未找到目标代码块，mem0 版本可能不同，请人工核对")
    WORK.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    run("docker", "cp", str(WORK), f"{CONTAINER}:{TARGET}")
    run("docker", "exec", CONTAINER, "touch", "/app/main.py")
    print("等待 uvicorn 重载...")
    time.sleep(6)
    print("OR 补丁已部署。验证：py eval/search_ab.py --tag search_jieba_or")


if __name__ == "__main__":
    main()