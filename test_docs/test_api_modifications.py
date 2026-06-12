#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAGFlow 改造验证脚本 — 测试节点级流式输出 + thinking 透传
用法: python test_api_modifications.py
"""

import requests
import json
import sys
import re
from datetime import datetime

# ======================== 配置 ========================
RAGFLOW_URL = "http://localhost:9380"
AGENT_ID = "02c3e74e659211f1b654a6b8be4f66ea"
API_KEY = "ragflow-Y1NTMwMTEyNjVhYTExZjFiYmI2MTJlOG"
QUESTION = "请根据环保法规，列出二氧化硫(SO2)排放限值。"

# ======================== 输出颜色 ========================
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def ok(msg):    print(f"  {GREEN}[PASS]{RESET} {msg}")
def fail(msg):  print(f"  {RED}[FAIL]{RESET} {msg}")
def warn(msg):  print(f"  {YELLOW}[WARN]{RESET} {msg}")
def info(msg):  print(f"  {CYAN}[INFO]{RESET} {msg}")


def parse_sse(response, label=""):
    """解析 SSE 流，返回 (final_answer, node_events, raw_lines)"""
    node_events = []
    final_answer = None
    running_events = 0
    raw_lines = []
    session_id = None

    buffer = ""
    for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
        if not chunk:
            continue
        buffer += chunk
        while "\n\n" in buffer:
            line, buffer = buffer.split("\n\n", 1)
            if line.startswith("data:"):
                data_str = line[5:].strip()
                raw_lines.append(data_str)
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                code = data.get("code", -1)
                if code == 500:
                    fail(f"服务端错误: {data.get('message', '')}")
                    continue

                inner = data.get("data", {})
                if inner is True:
                    break

                # 提取 session_id
                if "id" in inner and not session_id:
                    session_id = inner["id"]

                answer = inner.get("answer", "")

                # running_status 事件
                if inner.get("running_status"):
                    running_events += 1
                    if inner.get("node_completed"):
                        node_events.append({
                            "node_id": inner.get("node_id", ""),
                            "node_type": inner.get("node_type", ""),
                            "output": inner.get("output", {}),
                            "content": answer,
                        })
                        info(f"  [{label}] node_completed: type={inner.get('node_type')} "
                             f"id={inner.get('node_id','?')[:20]}...")
                    continue

                # 最终答案
                final_answer = {
                    "content": answer,
                    "reference": inner.get("reference", []),
                    "reasoning_content": inner.get("reasoning_content", ""),
                }
    return final_answer, node_events, raw_lines, session_id, running_events


def main():
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  RAGFlow 改造验证测试 — 两步流{RESET}")
    print(f"{BOLD}  API: {RAGFLOW_URL}{RESET}")
    print(f"{BOLD}  Agent: {AGENT_ID}{RESET}")
    print(f"{BOLD}  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{'='*60}\n")

    url = f"{RAGFLOW_URL}/api/v1/agents/{AGENT_ID}/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    # ==================== 第 1 步: 创建 session ====================
    print(f"{BOLD}第 1 步: 创建会话 (流式获取 session_id)...{RESET}")
    try:
        r1 = requests.post(url, headers=headers,
                          json={"question": "", "stream": True}, stream=True, timeout=30)
        # 解析 SSE 获取 session_id
        buffer1 = ""
        session_id = None
        for chunk in r1.iter_content(chunk_size=None, decode_unicode=True):
            if not chunk:
                continue
            buffer1 += chunk
            while "\n\n" in buffer1:
                line, buffer1 = buffer1.split("\n\n", 1)
                if line.startswith("data:"):
                    d = json.loads(line[5:].strip())
                    inner = d.get("data", {})
                    if "session_id" in inner:
                        session_id = inner["session_id"]
                        break
                    if inner is True:
                        break
            if session_id:
                break
        if not session_id:
            fail("未能获取 session_id")
            sys.exit(1)
        ok(f"会话已创建: {session_id[:24]}...")
    except Exception as e:
        fail(f"创建会话异常: {e}")
        sys.exit(1)

    # ==================== 第 2 步: 提问 (流式) ====================
    print(f"\n{BOLD}第 2 步: 发送问题 (流式)...{RESET}")
    print(f"  {QUESTION}\n")

    try:
        r2 = requests.post(url, headers=headers,
                          json={"question": QUESTION, "session_id": session_id, "stream": True, "sync_dsl": True},
                          stream=True, timeout=180)
        r2.raise_for_status()
    except Exception as e:
        fail(f"请求失败: {e}")
        sys.exit(1)

    final_answer, node_events, raw_lines, _, running_events = parse_sse(r2, label="Q")

    # ================== 结果汇总 ==================
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  测试结果{RESET}")
    print(f"{BOLD}{'='*60}\n")

    # --- 测试1: 节点级流式输出 ---
    print(f"{BOLD}[测试1] 全工作流节点级流式输出{RESET}")
    if node_events:
        ok(f"捕获到 {len(node_events)} 个 node_completed 事件:")
        for i, ev in enumerate(node_events):
            print(f"      #{i+1} node_type={ev['node_type']}")
    else:
        fail("未捕获到任何 node_completed 事件")

    # --- 测试2: thinking 透传 ---
    print(f"\n{BOLD}[测试2] LLM thinking 推理字段透传{RESET}")
    if final_answer is None:
        fail("未收到最终答案")
    else:
        reasoning = final_answer.get("reasoning_content", "")
        if reasoning:
            ok(f"reasoning_content 存在，长度: {len(reasoning)} 字符")
            preview = reasoning[:200].replace("\n", "\\n")
            print(f"      预览: {preview}...")
        else:
            warn("reasoning_content 为空 (可能使用的模型无 thinking 输出)")

        content = final_answer.get("content", "")
        if content:
            ok(f"返回内容长度: {len(content)} 字符")
            preview = content[:200].replace("\n", "\\n")
            print(f"      预览: {preview}...")

    # --- 测试3: SSE 原始数据 ---
    print(f"\n{BOLD}[测试3] 原始 SSE 数据抽样{RESET}")
    print(f"  共收到 {len(raw_lines)} 条数据事件 (running_status: {running_events})")

    has_new_fields = any("node_completed" in l or "reasoning_content" in l for l in raw_lines)
    if has_new_fields:
        ok("原始 SSE 数据中包含 node_completed 或 reasoning_content 字段")
    else:
        fail("原始 SSE 数据中未找到新字段")

    # --- 总结 ---
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  测试总结{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    passed = sum([bool(node_events), bool(final_answer and final_answer.get("reasoning_content")), has_new_fields])
    total = 3

    if passed == total:
        print(f"\n  {GREEN}{BOLD}全部通过！改造功能正常运行。{RESET}\n")
    else:
        print(f"\n  {YELLOW}{BOLD}通过 {passed}/{total}。{RESET}\n")
        if not node_events:
            info("提示: 检查 canvas.py / canvas_app.py / canvas_service.py 是否正确部署")
        if not final_answer or not final_answer.get("reasoning_content"):
            info("提示: thinking 需要 DeepSeek R1 等支持推理的模型")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
