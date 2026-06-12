#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAGFlow 节点实时输出观测 + JSON 保存
支持文件上传 (multipart/form-data)
"""
import requests, json, sys, os
from datetime import datetime

RAGFLOW_URL = "http://localhost:9380"
AGENT_ID = "6a6916d265ae11f189a6e676ff3a315b"
API_KEY = "ragflow-Y1NTMwMTEyNjVhYTExZjFiYmI2MTJlOG"
FILE_PATH = os.path.join(os.path.dirname(__file__), "环评报告_模拟.txt")
QUESTION = "请审核这份环评报告，指出是否符合环保标准，并提出修改建议。"

H = {"Authorization": f"Bearer {API_KEY}"}
SEP = "=" * 70
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_DIR = os.path.join(os.path.dirname(__file__), f"nodes_output_{TIMESTAMP}")
os.makedirs(OUT_DIR, exist_ok=True)

print(f"\n{SEP}")
print(f"  节点实时输出观测 + 文件上传")
print(f"  Agent: {AGENT_ID}")
print(f"  文件: {os.path.basename(FILE_PATH)}")
print(f"  问题: {QUESTION}")
print(f"  输出目录: {OUT_DIR}")
print(f"{SEP}\n")

# ==================== 第 1 步: 上传文件 + 创建 session ====================
print(f"[ 1 ] 创建会话 (上传文件)...")
with open(FILE_PATH, "rb") as f:
    r1 = requests.post(
        f"{RAGFLOW_URL}/api/v1/agents/{AGENT_ID}/sessions",
        headers=H,
        files={"License": (os.path.basename(FILE_PATH), f, "text/plain")},
        timeout=180,
    )
r1.raise_for_status()
data1 = r1.json()
if data1.get("code") != 0:
    print(f"  失败: {data1}")
    sys.exit(1)

session_id = data1["data"]["id"]
print(f"   OK! session_id: {session_id[:24]}...\n")

# ==================== 第 2 步: 流式提问 ====================
print(f"[ 2 ] 发送问题 (SSE 流式)...\n")
r2 = requests.post(
    f"{RAGFLOW_URL}/api/v1/agents/{AGENT_ID}/completions",
    headers={**H, "Content-Type": "application/json"},
    json={"question": QUESTION, "session_id": session_id, "stream": True, "sync_dsl": True},
    stream=True,
    timeout=300,
)
r2.raise_for_status()

# ==================== 解析 SSE ====================
node_index = 0
final_answer = ""  # 累积最终流式答案
final_reasoning = ""
running_text_shown = set()

buf = ""
for chunk in r2.iter_content(chunk_size=None, decode_unicode=True):
    if not chunk:
        continue
    buf += chunk
    while "\n\n" in buf:
        line, buf = buf.split("\n\n", 1)
        if not line.startswith("data:"):
            continue
        d = json.loads(line[5:])
        inner = d.get("data", {})
        if inner is True:
            break

        # --- 纯提示文本 (running_status 但没有 node_completed) ---
        if inner.get("running_status") and not inner.get("node_completed"):
            content = inner.get("content", "")
            if content and content not in running_text_shown:
                running_text_shown.add(content)
                print(f"  ... {content}")
            continue

        # --- 节点完成事件 ---
        if inner.get("node_completed"):
            node_index += 1
            t = inner.get("node_type", "?")
            oid = inner.get("node_id", "?")
            out = inner.get("output", {})

            print(f"\n{SEP}")
            print(f"  [{node_index}] {t}  (id: {oid})")
            print(f"{SEP}")

            # 打印输出内容
            if isinstance(out, list):
                for idx, item in enumerate(out):
                    if isinstance(item, dict):
                        content = item.get("content", "")
                        reasoning = item.get("reasoning_content", "")
                        if content:
                            # 截断过长内容
                            print(f"  [content] {content[:500]}" + ("..." if len(content) > 500 else ""))
                        if reasoning:
                            print(f"\n  [reasoning_content] {reasoning[:500]}" + ("..." if len(reasoning) > 500 else ""))
            elif isinstance(out, dict):
                if out.get("status") == "streaming":
                    print(f"  (流式输出节点，内容在下游实时传输)")
                else:
                    for k, v in out.items():
                        vs = str(v)
                        print(f"  [{k}] {vs[:500]}" + ("..." if len(vs) > 500 else ""))

            # 保存 JSON
            json_path = os.path.join(OUT_DIR, f"{node_index:02d}_{t}.json")
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(
                    {
                        "node_index": node_index,
                        "node_type": t,
                        "node_id": oid,
                        "output": out,
                        "timestamp": datetime.now().isoformat(),
                    },
                    jf,
                    ensure_ascii=False,
                    indent=2,
                )
            print(f"\n  >>> 已保存: {json_path}")
            continue

        # --- 最终答案流式累积 ---
        answer = inner.get("answer", "")
        if answer and not inner.get("running_status"):
            final_answer += answer
            if inner.get("reasoning_content"):
                final_reasoning = inner.get("reasoning_content", "")

# ==================== 最终答案 ====================
print(f"\n{SEP}")
print(f"  [最终答案]")
print(f"{SEP}")
if final_reasoning:
    print(f"\n  >>> 推理过程 (reasoning_content):")
    print(f"  {final_reasoning[:800]}" + ("..." if len(final_reasoning) > 800 else ""))
    print()
print(f"  >>> 回答 (content):")
print(f"  {final_answer[:2000]}" + ("..." if len(final_answer) > 2000 else ""))

# 保存最终答案
final_path = os.path.join(OUT_DIR, "final_answer.json")
with open(final_path, "w", encoding="utf-8") as jf:
    json.dump(
        {"content": final_answer, "reasoning_content": final_reasoning},
        jf,
        ensure_ascii=False,
        indent=2,
    )
print(f"\n  >>> 最终答案已保存: {final_path}")
print(f"\n  >>> 所有节点输出已保存至: {OUT_DIR}")
