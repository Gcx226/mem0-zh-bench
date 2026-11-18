"""mem0 中文多会话记忆评测 harness。

流程（每个用户）：
  1. reset：清空该 user_id 的旧记忆
  2. add：按 s1→s5 顺序写入会话，每次 add 后快照记忆，
     用事实 token 检查"埋入时是否被抽取"→ 抽取召回率
  3. search：每题检索 top5，用证据事实 token 判命中 → recall@5
  4. answer：DeepSeek 基于检索结果作答
  5. judge：Qwen（SiliconFlow）按黄金答案+判分标准裁决 → 回答准确率

只依赖标准库。运行：py eval/run_eval.py --tag baseline
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")

TOP_K = 5


def load_env():
    env = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    import os
    for k, v in os.environ.items():
        env.setdefault(k, v)
    env.setdefault("MEM0_API_URL", "http://localhost:8888")
    env.setdefault("LLM_BASE_URL", "https://api.deepseek.com/v1")
    env.setdefault("LLM_MODEL", "deepseek-chat")
    env.setdefault("JUDGE_BASE_URL", "https://api.siliconflow.cn/v1")
    env.setdefault("JUDGE_MODEL", "Qwen/Qwen2.5-72B-Instruct")
    return env


ENV = load_env()


def require_key(name):
    if not ENV.get(name):
        raise RuntimeError(f"{name} 未设置：请在 mem0-zh-bench/.env 填入")


def http_json(url, method="GET", body=None, headers=None, timeout=180, max_retries=3):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    last = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=data, method=method,
                                         headers=headers or {})
            if data is not None:
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                last = f"HTTP {e.code}: {detail}"
                time.sleep(3 * (attempt + 1))
                continue
            raise RuntimeError(f"HTTP {e.code} {method} {url}: {detail}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = str(e)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"请求失败（重试 {max_retries} 次）{method} {url}: {last}")


def mem0(method, path, body=None, params=None):
    url = ENV["MEM0_API_URL"].rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return http_json(url, method=method, body=body,
                     headers={"X-API-Key": ENV["MEM0_API_KEY"]})


def chat(base_key, model_key, messages, temperature=0.0, json_mode=True):
    base, key, model = ENV[base_key], ENV[model_key.replace("MODEL", "API_KEY")], ENV[model_key]
    body = {"model": model, "messages": messages, "temperature": temperature}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    data = http_json(base.rstrip("/") + "/chat/completions", method="POST", body=body,
                     headers={"Authorization": f"Bearer {key}"})
    return data["choices"][0]["message"]["content"]


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def memory_texts(payload):
    """兼容 {"results":[...]} / [...] 两种返回，抽出记忆文本列表。"""
    items = payload.get("results", payload) if isinstance(payload, dict) else payload
    out = []
    for m in items or []:
        if isinstance(m, dict):
            out.append(m.get("memory") or m.get("text") or "")
        elif isinstance(m, str):
            out.append(m)
    return [t for t in out if t]


def tokens_of(fact):
    tok = fact.get("token")
    if tok is None:
        return []
    return tok if isinstance(tok, list) else [tok]


def covered(fact, texts):
    toks = tokens_of(fact)
    return any(t in txt for txt in texts for t in toks)


def reset_user(uid):
    try:
        mem0("DELETE", "/memories", params={"user_id": uid})
        return
    except RuntimeError as e:
        if "HTTP 401" not in str(e) and "HTTP 403" not in str(e):
            raise
    # key 非 admin 时逐条删除
    payload = mem0("GET", "/memories", params={"user_id": uid})
    items = payload.get("results", payload) if isinstance(payload, dict) else payload
    for m in items or []:
        mid = m.get("id") if isinstance(m, dict) else None
        if mid:
            mem0("DELETE", f"/memories/{mid}")


def add_session(uid, session, instructions=None):
    body = {
        "messages": session["messages"],
        "user_id": uid,
        "metadata": {"session_id": session["session_id"], "date": session["date"]},
    }
    if instructions:
        body["prompt"] = instructions
    payload = mem0("POST", "/memories", body=body)
    items = payload.get("results", []) if isinstance(payload, dict) else []
    return len(items)


def search(uid, query):
    payload = mem0("POST", "/search", body={
        "query": query, "filters": {"user_id": uid}, "top_k": TOP_K,
    })
    items = payload.get("results", payload) if isinstance(payload, dict) else payload
    return items or []


ANSWER_PROMPT = """你是一个基于长期记忆回答问题的助手。下面是从记忆系统检索到的记忆片段：

{memories}

用户问题：{question}

要求：
1. 只依据上面的记忆片段回答，不要编造记忆中没有的信息。
2. 如果记忆片段中没有回答问题所需的信息，明确回答"不知道"或"没有相关记忆"。
3. 涉及时间时，以记忆内容中记载的日期为准。
4. 用中文简洁回答，一两句话即可。"""

JUDGE_PROMPT = """你是评测裁判。判断"系统回答"是否正确。

问题：{question}
参考答案：{answer}
判分标准：{scoring}
系统回答：{response}

裁决规则：
1. 严格按判分标准裁决，参考答案是唯一正确性标准。
2. 若参考答案是确定性答案，而系统回答"不知道/没有相关记忆"，判 wrong（除非题目本身要求拒答）。
3. 时间表述与参考答案语义等价即判对（如"9月21日那一周"与"9月底"、"8月24日至30日"与"8月下旬"）。
4. 系统回答包含参考答案要求的核心信息即可判对，不要求措辞一致；额外的正确背景信息不扣分。

只输出 JSON：{{"verdict": "correct" 或 "wrong", "reason": "简短理由"}}"""


def answer_question(question, retrieved):
    texts = memory_texts({"results": retrieved})
    mem_block = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts)) or "（无检索结果）"
    require_key("LLM_API_KEY")
    return chat("LLM_BASE_URL", "LLM_MODEL", [
        {"role": "user", "content": ANSWER_PROMPT.format(memories=mem_block, question=question)},
    ], temperature=0.2, json_mode=False).strip()


def judge_question(q, response):
    require_key("JUDGE_API_KEY")
    raw = chat("JUDGE_BASE_URL", "JUDGE_MODEL", [
        {"role": "user", "content": JUDGE_PROMPT.format(
            question=q["question"], answer=q["answer"],
            scoring=q["scoring"], response=response)},
    ], temperature=0.0)
    try:
        v = parse_json(raw)
        return v.get("verdict", "wrong").lower() == "correct", v.get("reason", "")
    except (json.JSONDecodeError, AttributeError):
        return False, f"裁判输出无法解析: {raw[:200]}"


def run_user(user, skip_add=False, max_questions=None, instructions=None):
    uid = user["user_id"]
    facts = {f["fact_id"]: f for f in user["facts"]}
    t0 = time.time()
    result = {"user_id": uid, "extraction": [], "questions": []}

    if not skip_add:
        reset_user(uid)
        print(f"  reset 完成")
        snapshots = {}
        for sid in user["eval_config"]["add_order"]:
            session = next(s for s in user["sessions"] if s["session_id"] == sid)
            n = add_session(uid, session, instructions=instructions)
            texts = memory_texts(mem0("GET", "/memories", params={"user_id": uid}))
            snapshots[sid] = texts
            print(f"  add {sid}（{session['date']}）→ 新增/变更 {n} 条，累计 {len(texts)} 条")
        for f in user["facts"]:
            hit = any(covered(f, snapshots.get(sid, [])) for sid in f["planted_in"])
            result["extraction"].append({"fact_id": f["fact_id"], "covered": hit})
    else:
        texts = memory_texts(mem0("GET", "/memories", params={"user_id": uid}))
        for f in user["facts"]:
            result["extraction"].append({"fact_id": f["fact_id"], "covered": covered(f, texts)})
        print(f"  skip-add：复用现有 {len(texts)} 条记忆（抽取召回按最终状态近似）")

    questions = user["questions"][:max_questions] if max_questions else user["questions"]
    for q in questions:
        retrieved = search(uid, q["question"])
        ret_texts = memory_texts({"results": retrieved})
        ev_facts = [facts[fid] for fid in q["evidence_facts"] if fid in facts]
        recall_hit = None
        if ev_facts:
            recall_hit = any(covered(f, ret_texts) for f in ev_facts)
        response = answer_question(q["question"], retrieved)
        correct, reason = judge_question(q, response)
        result["questions"].append({
            "qid": q["qid"], "type": q["type"],
            "recall_at_5": recall_hit,
            "retrieved": ret_texts,
            "response": response,
            "correct": correct, "judge_reason": reason,
        })
        mark = "✓" if correct else "✗"
        rmark = "-" if recall_hit is None else ("R✓" if recall_hit else "R✗")
        print(f"  {q['qid']} [{q['type']}] {rmark} {mark} {reason[:60]}")

    result["elapsed_sec"] = round(time.time() - t0, 1)
    return result


def summarize(results):
    ext_total = ext_hit = 0
    ret_total = ret_hit = 0
    ans_total = ans_hit = 0
    by_type = {}
    for r in results:
        for e in r["extraction"]:
            ext_total += 1
            ext_hit += e["covered"]
        for q in r["questions"]:
            ans_total += 1
            ans_hit += q["correct"]
            bt = by_type.setdefault(q["type"], {"total": 0, "correct": 0,
                                               "ret_total": 0, "ret_hit": 0})
            bt["total"] += 1
            bt["correct"] += q["correct"]
            if q["recall_at_5"] is not None:
                ret_total += 1
                ret_hit += q["recall_at_5"]
                bt["ret_total"] += 1
                bt["ret_hit"] += q["recall_at_5"]

    def pct(a, b):
        return round(a / b, 4) if b else None

    summary = {
        "users": len(results),
        "extraction_recall": pct(ext_hit, ext_total),
        "retrieval_recall_at_5": pct(ret_hit, ret_total),
        "answer_accuracy": pct(ans_hit, ans_total),
        "by_type": {
            t: {"answer_accuracy": pct(v["correct"], v["total"]),
                "retrieval_recall_at_5": pct(v["ret_hit"], v["ret_total"]),
                "n": v["total"]}
            for t, v in sorted(by_type.items())
        },
    }
    return summary


def main():
    ap = argparse.ArgumentParser(description="mem0 中文记忆评测")
    ap.add_argument("--tag", default="baseline", help="结果标签，输出 results/<tag>.json")
    ap.add_argument("--users", default=None, help="逗号分隔 user_id，默认全部")
    ap.add_argument("--skip-add", action="store_true", help="跳过 reset/add，复用已有记忆")
    ap.add_argument("--max-questions", type=int, default=None, help="每用户最多跑 N 题（冒烟用）")
    ap.add_argument("--instructions", default=None, help="自定义抽取指令文件路径（写入侧优化）")
    ap.add_argument("--data-dir", default=None, help="用户数据目录（默认 data/users；holdout 用 data/holdout）")
    args = ap.parse_args()

    instructions = None
    if args.instructions:
        instructions = Path(args.instructions).read_text(encoding="utf-8")

    data_dir = Path(args.data_dir) if args.data_dir else ROOT / "data" / "users"
    if not data_dir.is_absolute():
        data_dir = ROOT / data_dir

    require_key("MEM0_API_KEY")
    files = sorted(data_dir.glob("zh_*.json"))
    if args.users:
        wanted = {u.strip() for u in args.users.split(",")}
        files = [f for f in files if f.stem in wanted]
    if not files:
        raise RuntimeError("没有匹配的数据文件")

    print(f"评测 {len(files)} 个用户 | tag={args.tag} | skip_add={args.skip_add}")
    results = []
    for f in files:
        user = json.loads(f.read_text(encoding="utf-8"))
        print(f"\n=== {user['user_id']} {user['persona']['name']} ===")
        try:
            results.append(run_user(user, skip_add=args.skip_add,
                                    max_questions=args.max_questions,
                                    instructions=instructions))
        except RuntimeError as e:
            print(f"  失败：{e}")
            results.append({"user_id": user["user_id"], "error": str(e),
                            "extraction": [], "questions": []})

    summary = summarize(results)
    out = {
        "tag": args.tag,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "mem0_api_url": ENV["MEM0_API_URL"],
            "answer_model": ENV["LLM_MODEL"],
            "judge_model": ENV["JUDGE_MODEL"],
            "top_k": TOP_K,
            "skip_add": args.skip_add,
            "instructions": args.instructions,
            "data_dir": args.data_dir or "data/users",
        },
        "summary": summary,
        "users": results,
    }
    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{args.tag}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n========== 汇总 ==========")
    print(f"抽取召回率:     {summary['extraction_recall']}")
    print(f"检索 recall@5:  {summary['retrieval_recall_at_5']}")
    print(f"回答准确率:     {summary['answer_accuracy']}")
    for t, v in summary["by_type"].items():
        print(f"  {t:<12} 准确率 {v['answer_accuracy']}  recall@5 {v['retrieval_recall_at_5']}  (n={v['n']})")
    print(f"\n结果已写入 {out_path}")


if __name__ == "__main__":
    main()