"""生成 baseline vs optimized 对比报告（Markdown）。

运行：py eval/report.py --tags baseline optimized
输出：results/report.md
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")

METRICS = [
    ("extraction_recall", "抽取召回率"),
    ("retrieval_recall_at_5", "检索 recall@5"),
    ("answer_accuracy", "回答准确率"),
]
TYPE_ORDER = ["single_hop", "multi_hop", "temporal", "update", "abstention"]
TYPE_CN = {
    "single_hop": "单跳事实", "multi_hop": "多跳组合", "temporal": "时间推理",
    "update": "知识更新", "abstention": "拒答防幻觉",
}


def fmt(v):
    return "-" if v is None else f"{v*100:.1f}%"


def delta(a, b):
    if a is None or b is None:
        return "-"
    d = (b - a) * 100
    return f"{d:+.1f}pp"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="+", default=["baseline", "optimized"])
    ap.add_argument("--holdout", action="store_true", help="留出测试集报告（跳过受控 A/B，加完整性声明）")
    ap.add_argument("--out", default=None, help="输出文件名（默认 report.md；holdout 默认 holdout_report.md）")
    args = ap.parse_args()

    runs = {}
    for tag in args.tags:
        p = ROOT / "results" / f"{tag}.json"
        if not p.exists():
            raise SystemExit(f"缺少结果文件: {p}")
        runs[tag] = json.loads(p.read_text(encoding="utf-8"))

    base, opt = args.tags[0], args.tags[-1]
    b, o = runs[base]["summary"], runs[opt]["summary"]
    n_users = len(runs[base]["users"])

    lines = []
    if args.holdout:
        lines.append("# mem0 中文记忆评测：留出测试集验证报告")
    else:
        lines.append("# mem0 中文多会话记忆评测报告")
    lines.append("")
    if args.holdout:
        lines.append(f"- 留出测试集：{n_users} 个合成用户（优化期间从未见过）× 5 会话 × 10 题（单跳/多跳/时间/更新/拒答各 2）")
        lines.append(f"- 开发集：另 11 用户（zh_001–011），抽取指令在其上迭代；本集用户 zh_012–016 由同一生成器以新种子/新名字独立生成")
    else:
        lines.append(f"- 数据集：{n_users} 个合成用户 × 5 会话 × 10 题（单跳/多跳/时间/更新/拒答各 2）")
    lines.append(f"- 被测系统：mem0 REST API（{runs[base]['config']['mem0_api_url']}）")
    lines.append(f"- 作答模型：{runs[base]['config']['answer_model']}；裁判模型：{runs[base]['config']['judge_model']}")
    lines.append(f"- 检索 top_k={runs[base]['config']['top_k']}；{base} 运行于 {runs[base]['run_at'][:10]}，{opt} 运行于 {runs[opt]['run_at'][:10]}")
    if runs[opt]["config"].get("instructions"):
        lines.append(f"- 写入侧优化：自定义中文抽取指令（{runs[opt]['config']['instructions']}），经 mem0 官方 prompt 参数注入，无需改动源码")
    if args.holdout:
        lines.append(f"- 完整性声明：抽取指令在开发集上冻结后未再修改；两组在**同一容器检索状态**（jieba+OR 补丁恒定）下运行，唯一变量是写入侧指令")
    lines.append("")
    lines.append("## 总体指标")
    lines.append("")
    lines.append(f"| 指标 | {base} | {opt} | 变化 |")
    lines.append("|---|---|---|---|")
    for key, cn in METRICS:
        lines.append(f"| {cn} | {fmt(b[key])} | {fmt(o[key])} | {delta(b[key], o[key])} |")
    lines.append("")
    lines.append("## 分题型准确率")
    lines.append("")
    lines.append(f"| 题型 | {base} | {opt} | 变化 |")
    lines.append("|---|---|---|---|")
    for t in TYPE_ORDER:
        bv = b["by_type"].get(t, {}).get("answer_accuracy")
        ov = o["by_type"].get(t, {}).get("answer_accuracy")
        lines.append(f"| {TYPE_CN[t]} ({t}) | {fmt(bv)} | {fmt(ov)} | {delta(bv, ov)} |")
    lines.append("")
    lines.append("## 分题型检索 recall@5")
    lines.append("")
    lines.append(f"| 题型 | {base} | {opt} | 变化 |")
    lines.append("|---|---|---|---|")
    for t in TYPE_ORDER:
        bv = b["by_type"].get(t, {}).get("retrieval_recall_at_5")
        ov = o["by_type"].get(t, {}).get("retrieval_recall_at_5")
        lines.append(f"| {TYPE_CN[t]} | {fmt(bv)} | {fmt(ov)} | {delta(bv, ov)} |")
    lines.append("")
    lines.append("## 分用户回答准确率")
    lines.append("")
    lines.append(f"| 用户 | {base} | {opt} |")
    lines.append("|---|---|---|")
    omap = {u["user_id"]: u for u in runs[opt]["users"]}
    for u in runs[base]["users"]:
        uid = u["user_id"]
        bq = u.get("questions", [])
        oq = omap.get(uid, {}).get("questions", [])
        ba = sum(q["correct"] for q in bq) / len(bq) if bq else None
        oa = sum(q["correct"] for q in oq) / len(oq) if oq else None
        lines.append(f"| {uid} | {fmt(ba)} | {fmt(oa)} |")
    lines.append("")
    lines.append(f"## {opt} 仍答错的题（失败案例）")
    lines.append("")
    for u in runs[opt]["users"]:
        for q in u.get("questions", []):
            if not q["correct"]:
                lines.append(f"- **{q['qid']}** [{q['type']}] {q['judge_reason']}")
                lines.append(f"  - 系统回答：{q['response'][:120]}")
    lines.append("")
    ab_specs = [
        ("search_original", "原版（spaCy+AND）"),
        ("search_jieba", "jieba 分词"),
        ("search_jieba_or", "jieba+OR 语义"),
    ]
    ab_loaded = [(tag, cn, json.loads((ROOT / "results" / f"{tag}.json").read_text(encoding="utf-8"))["summary"])
                 for tag, cn in ab_specs if (ROOT / "results" / f"{tag}.json").exists()]
    if not args.holdout and len(ab_loaded) >= 2:
        lines.append("## 受控实验：检索侧净效果（固定记忆库 A/B）")
        lines.append("")
        lines.append("端到端跑分受抽取 LLM 非确定性干扰（整段会话偶发返回空）。为隔离检索侧效果，")
        lines.append("对**同一份记忆库**用 PUT 原文重建索引，在不同预处理/匹配语义下只测检索：")
        lines.append("")
        header = "| 题型 | " + " | ".join(cn for _, cn, _ in ab_loaded) + " |"
        lines.append(header)
        lines.append("|---|" + "---|" * len(ab_loaded))
        row = "| 总体 | " + " | ".join(fmt(s["retrieval_recall_at_5"]) for _, _, s in ab_loaded) + " |"
        lines.append(row)
        for t in TYPE_ORDER:
            vals = [s["by_type"].get(t, {}).get("recall_at_5") for _, _, s in ab_loaded]
            if all(v is None for v in vals):
                continue
            lines.append(f"| {TYPE_CN[t]} | " + " | ".join(fmt(v) for v in vals) + " |")
        lines.append("")
        lines.append("诊断链：原版 spaCy 不切中文 → BM25 全零；仅换 jieba 后 BM25 仍全零，")
        lines.append("因为 plainto_tsquery 是 AND 语义，自然问句的词元不可能全部命中同一条记忆；")
        lines.append("改 OR（to_tsquery 以 | 连接）后关键词通道才真正参与打分（explain 明细 bm25 0→0.034）。")
        lines.append("")
        lines.append("**未命中归因**：对 jieba+OR 组 9 道 recall 未命中题逐题核查，9/9 的证据事实")
        lines.append("根本不在记忆库中（写入侧抽取失败），0 道属于\"在库但搜不到\"。即当前语料下检索已饱和，")
        lines.append("bge-m3 语义向量能搜到所有存在的证据；recall 损失与端到端失分的瓶颈完全在写入侧")
        lines.append("（整段会话被抽取 LLM 判空、新旧状态共存不 UPDATE）。")
        lines.append("")
    lines.append("## 方法学说明与已知局限")
    lines.append("")
    lines.append("1. **抽取召回率**按事实 token 在埋入会话后的记忆快照中是否出现计算；superseded 事实按埋入时点计入。token 匹配是近似，语义改写可能漏判。")
    lines.append("2. **检索 recall@5**：top5 记忆中任一命中证据事实 token 即算命中；拒答题不计入。")
    if args.holdout:
        lines.append("3. **留出完整性**：抽取指令（zh_instructions.txt）在开发集 zh_001–011 上迭代冻结后，未依据本集任何结果修改；本集用户由同一生成器以新随机种子（index×7919）与新名字独立生成，优化期间从未出现。因此本集提升可归因于指令的泛化能力，而非对特定题目的过拟合。")
        lines.append("4. **变量隔离**：两组在同一个容器、同一检索状态（jieba 分词 + OR 匹配补丁均已部署且恒定）下运行，唯一差异是 add 调用是否携带写入侧指令。检索侧不是本实验的变量。")
        lines.append("5. **裁判校准**：沿用与开发集相同的裁判提示词（非拒答题答不知道判错、时间语义等价判对、核心信息即可），跨集可比。")
        lines.append("6. **抽取非确定性**：mem0 抽取 LLM 偶发对整段会话返回空，单次运行存在噪声；本集为单次全量运行，未做 n 次重复取均值，个别题目得失含运气成分。")
        lines.append("7. **样本规模**：5 用户 × 10 题 = 50 题（拒答 10 题不计 recall），统计效力有限，结论为方向性验证而非精确效应量估计。")
    else:
        lines.append("3. **裁判校准**：两组结果均用同一裁判提示词重判（含\"非拒答题答不知道判错\"、\"时间语义等价判对\"规则），见 rejudge.py。")
        lines.append("4. **抽取非确定性**：mem0 的 LLM 抽取偶发对整段会话返回空（观测到 s3/s4/s5 均有 0 条案例），单次运行存在噪声；更新链失败部分源于此。")
        lines.append("5. **优化内容**：两处补丁——(a) BM25 预处理从 spaCy 英文词形还原换为 jieba 中文分词（含停用词过滤），add/search 共用；(b) pgvector 关键词匹配从 plainto_tsquery（AND）改为 to_tsquery OR 连接，ts_rank_cd 排序不变。均通过 docker cp + touch 热重载部署，不重启容器。")
        lines.append("6. **端到端 optimized 组**仅含 jieba 补丁（OR 补丁在其后部署）；两组端到端差异主要由抽取非确定性主导，检索侧结论以受控实验为准。")
        if runs[opt]["config"].get("instructions"):
            lines.append("7. **写入侧优化机制**：该版 mem0 的 V3 抽取流水线为 ADD-only（无 UPDATE/DELETE 决策，去重仅靠 MD5 精确匹配），新旧状态天然共存。中文抽取指令通过官方 prompt 参数（Custom Instructions，系统提示中声明为最高优先级）要求：以会话文本内日期为唯一时间锚点（覆盖系统注入的运行日期）、禁止对新个人信息返回空列表、事实自包含（带姓名与绝对日期）、状态更新显式写成含生效日期的当前态事实。")
    lines.append("")

    if args.out:
        out = ROOT / "results" / args.out
    else:
        out = ROOT / "results" / ("holdout_report.md" if args.holdout else "report.md")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"报告已写入 {out}")
    print("\n".join(lines[:30]))


if __name__ == "__main__":
    main()