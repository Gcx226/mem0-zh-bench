import argparse
import json
import sys
from pathlib import Path

import dialogue
import skeleton
import validate

ROOT = Path(__file__).resolve().parent.parent
USERS = ROOT / "data" / "users"
SKELS = ROOT / "data" / "skeletons"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="批量生成中文记忆评测用户")
    ap.add_argument("--count", type=int, default=10, help="生成用户数")
    ap.add_argument("--start", type=int, default=2, help="起始编号（zh_001 为已审样例）")
    ap.add_argument("--offline", action="store_true", help="只生成骨架+问题，不调用 LLM 写对话")
    ap.add_argument("--out-dir", default=None, help="用户输出目录（默认 data/users；holdout 用 data/holdout）")
    args = ap.parse_args()

    out_users = Path(args.out_dir) if args.out_dir else USERS
    if not out_users.is_absolute():
        out_users = ROOT / out_users

    results = []
    for i in range(args.start, args.start + args.count):
        uid = f"zh_{i:03d}"
        user = skeleton.build_user(i)
        if args.offline:
            SKELS.mkdir(parents=True, exist_ok=True)
            (SKELS / f"{uid}.json").write_text(json.dumps(user, ensure_ascii=False, indent=2), encoding="utf-8")
            res = validate.validate(user, skeleton_only=True)
        else:
            dialogue.fill_dialogues(user)
            out_users.mkdir(parents=True, exist_ok=True)
            (out_users / f"{uid}.json").write_text(json.dumps(user, ensure_ascii=False, indent=2), encoding="utf-8")
            res = validate.validate(user)
        results.append((uid, res))
        mark = "OK " if res["status"] == "PASS" else "FLAG"
        print(f"[{mark}] {uid}  {user['persona']['name']}  {user['persona']['city']}→{user['persona']['hometown']}")
        for fl in res["flags"]:
            print(f"        - {fl}")

    passed = sum(1 for _, r in results if r["status"] == "PASS")
    out = SKELS if args.offline else out_users
    print(f"\n完成：{passed}/{len(results)} PASS，输出目录 {out}")
    if not args.offline and passed < len(results):
        print("存在 FLAG 用户：请人工复核 flags 后再纳入评测（抽检至少 20%）。")


if __name__ == "__main__":
    main()