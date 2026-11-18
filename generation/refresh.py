import json
import sys
from pathlib import Path

import skeleton
import validate

ROOT = Path(__file__).resolve().parent.parent
USERS = ROOT / "data" / "users"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    processed = passed = 0
    for fp in sorted(USERS.glob("zh_*.json")):
        old = json.loads(fp.read_text(encoding="utf-8"))
        if old["user_id"] == "zh_001":
            continue
        index = int(old["user_id"].split("_")[1])
        msgs = {s["session_id"]: s["messages"] for s in old["sessions"]}
        new = skeleton.build_user(index)
        for s in new["sessions"]:
            s["messages"] = msgs.get(s["session_id"], [])
        res = validate.validate(new)
        fp.write_text(json.dumps(new, ensure_ascii=False, indent=2), encoding="utf-8")
        processed += 1
        passed += res["status"] == "PASS"
        mark = "OK " if res["status"] == "PASS" else "FLAG"
        print(f"[{mark}] {new['user_id']}  {new['persona']['name']}")
        for fl in res["flags"]:
            print(f"        - {fl}")
    print(f"\n刷新完成：{passed}/{processed} PASS（保留原对话，zh_001 手工样例不动）")


if __name__ == "__main__":
    main()