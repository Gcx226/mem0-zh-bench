"""用更新后的裁判提示词重判已有结果（不重跑 mem0，只重判保存的回答）。

用途：裁判校准后保证 baseline 与 optimized 用同一把尺子。
运行：py eval/rejudge.py --tag baseline
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
sys.stdout.reconfigure(encoding="utf-8")

import run_eval as r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()

    path = ROOT / "results" / f"{args.tag}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    qmap = {}
    for f in (ROOT / "data" / "users").glob("zh_*.json"):
        u = json.loads(f.read_text(encoding="utf-8"))
        for q in u["questions"]:
            qmap[q["qid"]] = q

    changed = 0
    for u in data["users"]:
        for item in u.get("questions", []):
            q = qmap.get(item["qid"])
            if not q:
                continue
            correct, reason = r.judge_question(q, item["response"])
            if correct != item["correct"]:
                changed += 1
                print(f"{item['qid']}: {'✓→✗' if item['correct'] else '✗→✓'} {reason[:70]}")
            item["correct"] = correct
            item["judge_reason"] = reason

    data["summary"] = r.summarize(data["users"])
    data["rejudged"] = True
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    s = data["summary"]
    print(f"\n重判完成，{changed} 题改判。回答准确率: {s['answer_accuracy']}")
    for t, v in s["by_type"].items():
        print(f"  {t:<12} {v['answer_accuracy']} (n={v['n']})")


if __name__ == "__main__":
    main()