from datetime import date, timedelta

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def validate(user, skeleton_only=False):
    flags = []
    fids = {f["fact_id"] for f in user["facts"]}
    sids = {s["session_id"] for s in user["sessions"]}

    for f in user["facts"]:
        if f.get("superseded_by") and f["superseded_by"] not in fids:
            flags.append(f"{f['fact_id']} superseded_by 指向不存在的事实")
        for s in f["planted_in"]:
            if s not in sids:
                flags.append(f"{f['fact_id']} planted_in 指向不存在的会话 {s}")
    for q in user["questions"]:
        for f in q["evidence_facts"]:
            if f not in fids:
                flags.append(f"{q['qid']} evidence_facts 指向不存在的事实 {f}")
        for s in q["evidence_sessions"]:
            if s not in sids:
                flags.append(f"{q['qid']} evidence_sessions 指向不存在的会话 {s}")

    dates = [date.fromisoformat(s["date"]) for s in user["sessions"]]
    if dates != sorted(dates):
        flags.append("会话日期非递增")
    for s, d in zip(user["sessions"], dates):
        if s["weekday"] != WEEKDAYS[d.weekday()]:
            flags.append(f"{s['session_id']} 星期标注错误")

    types = {}
    for q in user["questions"]:
        types[q["type"]] = types.get(q["type"], 0) + 1
    if types != {"single_hop": 2, "multi_hop": 2, "temporal": 2, "update": 2, "abstention": 2}:
        flags.append(f"题型配比异常: {types}")

    if not skeleton_only:
        for s in user["sessions"]:
            if not s["messages"]:
                flags.append(f"{s['session_id']} 无对话")
                continue
            roles = [m["role"] for m in s["messages"]]
            if roles[0] != "user":
                flags.append(f"{s['session_id']} 未以 user 开始")
            if not 6 <= len(s["messages"]) <= 12:
                flags.append(f"{s['session_id']} 消息数 {len(s['messages'])} 超出 6-12")

        alltext = " ".join(m["content"] for s in user["sessions"] for m in s["messages"])
        for t in user["abstention_topics"]:
            for w in t["words"]:
                if w in alltext:
                    flags.append(f"拒答题话题泄漏: {w}（{t['topic']}）")

        for f in user["facts"]:
            tok = f.get("token")
            if not tok:
                continue
            toks = tok if isinstance(tok, list) else [tok]
            planted = " ".join(
                m["content"] for s in user["sessions"]
                if s["session_id"] in f["planted_in"]
                for m in s["messages"] if m["role"] == "user"
            )
            if not any(t in planted for t in toks):
                flags.append(f"事实可能未传达: {f['fact_id']}（关键词 {toks}）")

        sd = {s["session_id"]: date.fromisoformat(s["date"]) for s in user["sessions"]}
        comp = sd["s5"] - timedelta(days=1)
        tm = (sd["s3"] - timedelta(days=sd["s3"].weekday())) + timedelta(days=14)
        comp_str = f"{comp.month}月{comp.day}日"
        tm_str = f"{tm.month}月{tm.day}日"
        for s in user["sessions"]:
            for m in s["messages"]:
                if comp_str in m["content"]:
                    flags.append(f"绝对日期泄漏 {comp_str} 于 {s['session_id']}（q05 失效）")
                if tm_str in m["content"]:
                    flags.append(f"绝对日期泄漏 {tm_str} 于 {s['session_id']}（q06 失效）")

    return {"status": "FLAG" if flags else "PASS", "flags": flags}