import json
from pathlib import Path

import llm

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = json.loads((ROOT / "data" / "users" / "zh_001.json").read_text(encoding="utf-8"))

SYSTEM = (
    "你是中文对话数据生成器，为记忆系统评测基准生成自然、口语化的用户-助手对话。"
    "只输出 JSON 对象，格式 {\"messages\":[{\"role\":\"user\",\"content\":\"...\"},{\"role\":\"assistant\",\"content\":\"...\"}]}。"
)


def fill_dialogues(user):
    persona = user["persona"]
    forbidden = [w for t in user["abstention_topics"] for w in t["words"]]
    prior = []
    for idx, s in enumerate(user["sessions"]):
        example = EXAMPLE["sessions"][idx]["messages"]
        plant = "\n".join("- " + p["hint"] for p in s["plant"])
        phenomena = "\n".join("- " + p for p in s["phenomena"])
        prior_text = json.dumps(prior, ensure_ascii=False) if prior else "（这是第一个会话）"
        prompt = f"""人设：{json.dumps(persona, ensure_ascii=False)}
会话日期：{s['date_cn']}（{s['weekday']}）

本会话要传达的事实（用口语自然带出，不要逐字念，不要新增未列出的个人事实）：
{plant}

必须嵌入的语言现象：
{phenomena}

禁止提及的话题/词（这些是拒答题考点，对话里绝不能出现）：{', '.join(forbidden)}

之前会话的内容（供指代衔接，不要重复其事实）：
{prior_text}

参考风格（只学语气和节奏，不要照抄内容）：
{json.dumps(example, ensure_ascii=False)}

硬性要求：
1. 6-10 条消息，user/assistant 交替，以 user 开始、以 assistant 结束。
2. 第一条 user 消息自然带出日期，例如"今天{s['date_cn']}，{s['weekday']}，……"。
3. 助手回复简短、有帮助，可复述稳定事实；但【禁止】把相对时间换算成绝对日期（不要说"也就是X月X日"），保留"昨天/下下周/过两天/月底/下个月"原样，留给抽取模型推理。
4. 像真人跟 AI 助手聊天，自然口语，避免翻译腔和书面腔。
5. 只输出 JSON。"""
        content = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}], temperature=0.9)
        msgs = llm.parse_json(content)["messages"]
        s["messages"] = msgs
        prior.append({"date": s["date_cn"], "messages": msgs})
    return user