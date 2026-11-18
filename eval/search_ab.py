"""检索侧受控 A/B 实验：固定同一份记忆库，只切换分词函数。

原理：mem0 的 PUT /memories/{id} 会用当前加载的 lemmatize_for_bm25
重建该条记忆的 text_lemmatized 索引字段。因此：
  1. 对全部记忆 PUT 原文（文本不变，仅重建索引）→ 当前代码的索引
  2. 逐题 search，算 recall@5
在"原版代码"和"jieba 补丁"下各做一遍，记忆文本完全相同，
唯一变量是分词方式 → 差值即检索侧净效果，排除抽取噪声。

运行：py eval/search_ab.py --tag search_original
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
sys.stdout.reconfigure(encoding="utf-8")

import run_eval as r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()

    files = sorted((ROOT / "data" / "users").glob("zh_*.json"))
    results = []
    t0 = time.time()
    for f in files:
        user = json.loads(f.read_text(encoding="utf-8"))
        uid = user["user_id"]
        facts = {x["fact_id"]: x for x in user["facts"]}
        payload = r.mem0("GET", "/memories", params={"user_id": uid})
        items = payload.get("results", payload) if isinstance(payload, dict) else payload
        items = [m for m in (items or []) if isinstance(m, dict) and m.get("id")]

        reindexed = failed = 0
        for m in items:
            text = m.get("memory") or m.get("text") or ""
            try:
                r.mem0("PUT", f"/memories/{m['id']}", body={"text": text})
                reindexed += 1
            except RuntimeError:
                failed += 1
        print(f"{uid}: 重建索引 {reindexed} 条（失败 {failed}）")

        ures = {"user_id": uid, "questions": []}
        for q in user["questions"]:
            ev = [facts[fid] for fid in q["evidence_facts"] if fid in facts]
            if not ev:
                continue
            retrieved = r.search(uid, q["question"])
            texts = r.memory_texts({"results": retrieved})
            hit = any(r.covered(f, texts) for f in ev)
            ures["questions"].append({"qid": q["qid"], "type": q["type"],
                                      "recall_at_5": hit})
        n = len(ures["questions"])
        h = sum(q["recall_at_5"] for q in ures["questions"])
        print(f"  recall@5: {h}/{n}")
        results.append(ures)

    total = sum(len(u["questions"]) for u in results)
    hits = sum(q["recall_at_5"] for u in results for q in u["questions"])
    by_type = {}
    for u in results:
        for q in u["questions"]:
            bt = by_type.setdefault(q["type"], [0, 0])
            bt[0] += 1
            bt[1] += q["recall_at_5"]
    summary = {
        "retrieval_recall_at_5": round(hits / total, 4) if total else None,
        "n": total,
        "by_type": {t: {"recall_at_5": round(h / n, 4), "n": n}
                    for t, (n, h) in sorted(by_type.items())},
    }
    out = {"tag": args.tag, "kind": "search_only_controlled",
           "run_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "elapsed_sec": round(time.time() - t0, 1),
           "summary": summary, "users": results}
    p = ROOT / "results" / f"{args.tag}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n总 recall@5: {summary['retrieval_recall_at_5']} ({hits}/{total})")
    for t, v in summary["by_type"].items():
        print(f"  {t:<12} {v['recall_at_5']} (n={v['n']})")
    print(f"已写入 {p}")


if __name__ == "__main__":
    main()