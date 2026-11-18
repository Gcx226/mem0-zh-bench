"""评测 API（FastAPI）：把评测流水线封装成 HTTP 服务。

启动：py -m uvicorn eval.api:app --port 8900
（在 mem0-zh-bench 目录下运行；或 py eval/api.py）

端点：
  POST /eval/run          提交评测任务（同一时间只允许一个，mem0 状态共享）
  GET  /eval/jobs/{id}    查询任务状态 + 日志尾部
  GET  /eval/results/{tag} 读取结果 JSON
  GET  /eval/report       生成并返回 Markdown 对比报告
"""
import json
import subprocess
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
JOBS = {}

app = FastAPI(title="mem0 中文多会话记忆评测 API", version="0.1")


class RunRequest(BaseModel):
    tag: str = "baseline"
    users: list[str] | None = None
    skip_add: bool = False
    max_questions: int | None = None


def _running_job():
    for jid, j in JOBS.items():
        if j["proc"].poll() is None:
            return jid
    return None


@app.post("/eval/run")
def start_run(req: RunRequest):
    busy = _running_job()
    if busy:
        raise HTTPException(409, f"已有评测任务在跑（job {busy}），mem0 状态共享，禁止并行")
    if not req.tag.replace("_", "").isalnum():
        raise HTTPException(400, "tag 只允许字母数字下划线")
    job_id = uuid.uuid4().hex[:8]
    cmd = [sys.executable, str(ROOT / "eval" / "run_eval.py"), "--tag", req.tag]
    if req.users:
        cmd += ["--users", ",".join(req.users)]
    if req.skip_add:
        cmd.append("--skip-add")
    if req.max_questions:
        cmd += ["--max-questions", str(req.max_questions)]
    RESULTS.mkdir(exist_ok=True)
    log_path = RESULTS / f"job_{job_id}.log"
    log_f = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, cwd=ROOT)
    JOBS[job_id] = {"tag": req.tag, "proc": proc, "log": log_path, "log_f": log_f}
    return {"job_id": job_id, "tag": req.tag, "cmd": cmd}


@app.get("/eval/jobs/{job_id}")
def job_status(job_id: str):
    j = JOBS.get(job_id)
    if not j:
        raise HTTPException(404, "任务不存在")
    code = j["proc"].poll()
    status = "running" if code is None else ("completed" if code == 0 else "failed")
    tail = ""
    if j["log"].exists():
        tail = "\n".join(j["log"].read_text(encoding="utf-8", errors="replace").splitlines()[-15:])
    return {"job_id": job_id, "tag": j["tag"], "status": status,
            "exit_code": code, "log_tail": tail}


@app.get("/eval/jobs")
def list_jobs():
    return [{"job_id": jid, "tag": j["tag"],
             "status": "running" if j["proc"].poll() is None else
             ("completed" if j["proc"].returncode == 0 else "failed")}
            for jid, j in JOBS.items()]


@app.get("/eval/results/{tag}")
def get_results(tag: str):
    p = RESULTS / f"{tag}.json"
    if not p.exists():
        raise HTTPException(404, f"没有 {tag} 的结果")
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/eval/report", response_class=PlainTextResponse)
def get_report():
    if not (RESULTS / "baseline.json").exists() or not (RESULTS / "optimized.json").exists():
        raise HTTPException(404, "需要 baseline 和 optimized 结果齐全才能出报告")
    subprocess.run([sys.executable, str(ROOT / "eval" / "report.py")],
                   check=True, cwd=ROOT, capture_output=True)
    return (RESULTS / "report.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8900)