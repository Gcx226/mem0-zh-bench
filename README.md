# mem0-zh-bench：中文多会话记忆评测基准与优化

面向 AI Agent 长期记忆系统的**评测基准 + 检索/写入侧优化**，基于开源记忆框架 [mem0](https://github.com/mem0ai/mem0) 二次开发。

核心不是"调参涨点"，而是一套可复现的评测方法论：**构建基准 → 跑基线 → 受控实验定位瓶颈 → 定向优化 → 留出测试集验证泛化**。

## 关键结果

写入侧优化（经 mem0 官方 `prompt` 扩展点注入中文抽取指令，**不改源码**）在开发集与留出集上均显著提升：

### 开发集（11 用户 × 5 会话 × 110 题）

| 指标 | baseline | write_opt | 变化 |
|---|---|---|---|
| 回答准确率 | 84.5% | **97.3%** | +12.7pp |
| 检索 recall@5 | 96.6% | **100.0%** | +3.4pp |
| 抽取召回率 | 90.0% | 93.8% | +3.8pp |

| 题型 | baseline | write_opt |
|---|---|---|
| 知识更新 | 59.1% | **95.5%** (+36.4pp) |
| 时间推理 | 72.7% | **100.0%** (+27.3pp) |
| 多跳组合 | 90.9% | 100.0% |
| 单跳事实 | 100.0% | 90.9% |
| 拒答防幻觉 | 100.0% | 100.0% |

### 留出测试集（5 个优化期间从未见过的用户，zh_012–016）

抽取指令在开发集上**冻结后未再修改**，holdout 用户由同一生成器以新随机种子 + 新名字独立生成，两组共享同一容器检索状态。

| 指标 | baseline | write_opt | 变化 |
|---|---|---|---|
| 回答准确率 | 78.0% | **94.0%** | +16.0pp |
| 检索 recall@5 | 87.5% | **100.0%** | +12.5pp |
| 抽取召回率 | 84.2% | 92.6% | +8.4pp |

| 题型 | baseline | write_opt |
|---|---|---|
| 多跳组合 | 70.0% | **100.0%** (+30pp) |
| 时间推理 | 70.0% | 90.0% (+20pp) |
| 知识更新 | 60.0% | 80.0% (+20pp) |
| 单跳事实 | 90.0% | 100.0% |
| 拒答防幻觉 | 100.0% | 100.0% |

**提升泛化成立**——留出集准确率增幅（+16pp）甚至大于开发集（+12.7pp），证明优化不是对自设基准的过拟合。详见 [results/report.md](results/report.md) 与 [results/holdout_report.md](results/holdout_report.md)。

## 方法学亮点

### 1. 受控 A/B 实验定位瓶颈（含诚实的负结果）

端到端跑分受抽取 LLM 非确定性干扰。为隔离检索侧效果，对**同一份记忆库**用 PUT 原文重建索引，只变检索预处理：

| 检索配置 | recall@5 |
|---|---|
| 原版（spaCy + AND） | 89.8% |
| jieba 分词 | 89.8% |
| jieba + OR 语义 | 89.8% |

诊断链：原版 spaCy 不切中文 → BM25 全零；仅换 jieba 仍全零，因为 `plainto_tsquery` 是 AND 语义，自然问句词元不可能全部命中同一条记忆；改 OR（`to_tsquery` 以 `|` 连接）后关键词通道才真正参与打分（explain 明细 bm25 0→0.034）。

**未命中归因**：对 9 道 recall 未命中题逐题核查，9/9 的证据事实根本不在记忆库中（写入侧抽取失败），0 道属于"在库但搜不到"。结论：当前语料下检索已被 bge-m3 语义向量饱和，瓶颈完全在写入侧。这个负结果直接把优化方向从检索侧转向写入侧。

### 2. 源码级架构理解

读 mem0 V3 抽取流水线源码发现其为 **ADD-only**（无 UPDATE/DELETE 决策，去重仅靠 MD5 精确匹配），新旧状态天然共存——这是更新题基线仅 59% 的根因。优化选择官方 `prompt` 扩展点（Custom Instructions，系统提示中声明最高优先级）而非改源码，重启不失效。

### 3. 写入侧中文抽取指令

[eval/zh_instructions.txt](eval/zh_instructions.txt) 四条规则：
- **日期锚定**：以会话文本内日期为唯一时间锚点，覆盖系统注入的真实运行日期（治时间推理题）
- **抽取完整性**：禁止对新个人信息返回空列表（治整段会话被丢弃）
- **事实自包含**：带姓名 + 绝对日期
- **更新显式化**：状态变化写成含生效日期的当前态事实（治新旧共存）

### 4. 评测流水线

全自动：reset → 按序 add 会话并快照（抽取召回率）→ 每题 search top5（recall@5）→ DeepSeek 作答 → Qwen2.5-72B 裁判（回答准确率）。裁判提示词经校准（非拒答题答"不知道"判错、时间语义等价判对、核心信息即可），跨轮次/跨集可比。

## 项目结构

```
mem0-zh-bench/
├── data/
│   ├── users/          # 开发集 zh_001–011（人设+5会话+事实账本+10题）
│   ├── holdout/        # 留出集 zh_012–016（优化期间从未见过）
│   └── skeletons/      # 离线骨架
├── generation/         # 模板驱动数据生成器
│   ├── skeleton.py     #   人设/事实/问题骨架（index×7919 随机种子）
│   ├── dialogue.py     #   LLM 填充口语化对话（嵌入主语省略/模糊时间/指代等现象）
│   ├── generate.py     #   批量生成入口（--out-dir 隔离 holdout）
│   └── validate.py     #   严格校验（事实埋入/拒答泄漏/绝对日期泄漏）
├── eval/
│   ├── run_eval.py     # 核心评测 harness（纯标准库，--data-dir/--instructions）
│   ├── search_ab.py    # 固定记忆库受控检索 A/B
│   ├── rejudge.py      # 裁判重判（校准提示词变更后可比）
│   ├── report.py       # 对比报告生成（--holdout 模式）
│   ├── api.py          # FastAPI 评测服务
│   └── zh_instructions.txt  # 写入侧中文抽取指令
├── optimization/       # 检索侧补丁（热重载部署 + 一键回滚）
│   ├── apply_zh_patch.py    # jieba 中文分词
│   ├── apply_or_patch.py    # pgvector OR 匹配
│   ├── revert_zh_patch.py   # 还原原版
│   └── *_backup.py          # 原文件备份
└── results/            # 各轮结果 JSON + 对比报告
```

## 复现步骤

### 前置

1. 部署自托管 mem0栈（参考 [mem0 server](https://github.com/mem0ai/mem0)）：API `localhost:8888`、dashboard `localhost:3000`、pgvector Postgres。配置 LLM（DeepSeek）、embedder（SiliconFlow `BAAI/bge-m3`）、启用 API key 认证。
2. Python 3.10+。harness 与生成器**纯标准库**；评测 API 额外需 `fastapi uvicorn pydantic`。

### 配置

```bash
cp .env.example .env
# 填入 MEM0_API_KEY、LLM_API_KEY、JUDGE_API_KEY（见 .env.example 注释）
```

### 部署检索补丁（可选，写入侧优化不依赖它）

```bash
py optimization/apply_zh_patch.py    # jieba 分词，自动验证
py optimization/apply_or_patch.py    # OR 匹配
# 回滚：py optimization/revert_zh_patch.py
```

> 补丁通过 `docker cp` + `touch /app/main.py` 热重载部署，**不重启容器**（该 mem0 部署每次启动会 `pip --force-reinstall` 抹掉 site-packages 改动）。Git Bash 中 docker exec 含 Linux 路径时前缀 `MSYS_NO_PATHCONV=1`。

### 生成数据（仓库已含生成结果，可跳过）

```bash
py generation/generate.py --start 2 --count 10                       # 开发集
py generation/generate.py --start 12 --count 5 --out-dir data/holdout # 留出集
```

### 跑评测

```bash
# 开发集
py eval/run_eval.py --tag baseline
py eval/run_eval.py --tag write_opt --instructions eval/zh_instructions.txt
py eval/report.py --tags baseline write_opt

# 留出集（指令冻结，同一检索状态）
py eval/run_eval.py --tag baseline_holdout --data-dir data/holdout
py eval/run_eval.py --tag write_opt_holdout --data-dir data/holdout --instructions eval/zh_instructions.txt
py eval/report.py --holdout --tags baseline_holdout write_opt_holdout
```

### 评测 API（可选）

```bash
py -m uvicorn eval.api:app --port 8900
# POST /eval/run 提交任务 · GET /eval/jobs/{id} 查进度 · GET /eval/report 取报告
```

> Windows 建议设 `PYTHONUTF8=1` 避免 GBK  locale 破坏中文输出；用 `py` 启动器（非 Microsoft Store 的 `python` 占位）。

## 已知局限（诚实声明）

- **合成模板数据**：非真实用户对话，模板驱动生成，规模有限（开发 110 题 + 留出 50 题）。
- **单次运行噪声**：mem0 抽取 LLM 偶发对整段会话返回空。留出集唯一回退用户 zh_013（90%→70%）的 3 道错题全部因其 s5 会话在该次运行被判空（相关事实均埋在 s5），属抽取非确定性而非指令缺陷。未做 n 次重复取均值。
- **token 匹配近似**：抽取召回率/recall@5 按事实关键词命中计算，语义改写可能漏判。
- **版本相关**：检索补丁针对特定 mem0 版本的源码块，版本变更需人工核对。

## 技术栈

Python · FastAPI · mem0 · pgvector · bge-m3 · DeepSeek · Qwen2.5-72B（SiliconFlow）· jieba · Docker