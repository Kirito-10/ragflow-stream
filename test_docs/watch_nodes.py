#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAGFlow 节点实时输出观测脚本
每完成一个节点立即打印该节点的输出内容
"""
import requests, json, sys

RAGFLOW_URL = "http://localhost:9380"
AGENT_ID = "02c3e74e659211f1b654a6b8be4f66ea"
API_KEY = "ragflow-Y1NTMwMTEyNjVhYTExZjFiYmI2MTJlOG"
QUESTION = "请根据环保法规，列出二氧化硫(SO2)排放限值。"

H = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
URL = f'{RAGFLOW_URL}/api/v1/agents/{AGENT_ID}/completions'

SEP = "=" * 70

print(f"\n{SEP}")
print(f"  节点实时输出观测")
print(f"  问题: {QUESTION}")
print(f"{SEP}\n")

# --- Step 1: 创建会话 ---
r1 = requests.post(URL, headers=H, json={'question': '', 'stream': True}, stream=True, timeout=30)
buf = ''; sid = None
for c in r1.iter_content(chunk_size=None, decode_unicode=True):
    if not c: continue
    buf += c
    while '\n\n' in buf:
        line, buf = buf.split('\n\n', 1)
        if line.startswith('data:'):
            d = json.loads(line[5:])
            inner = d.get('data', {})
            if inner is True: break
            sid = inner.get('session_id')
            if sid: break
    if sid: break

# --- Step 2: 提问 ---
r2 = requests.post(URL, headers=H, json={
    'question': QUESTION, 'session_id': sid, 'stream': True, 'sync_dsl': True
}, stream=True, timeout=180)

buf = ''; node_index = 0; final_answer = None; final_reasoning = ''
for c in r2.iter_content(chunk_size=None, decode_unicode=True):
    if not c: continue
    buf += c
    while '\n\n' in buf:
        line, buf = buf.split('\n\n', 1)
        if line.startswith('data:'):
            d = json.loads(line[5:])
            inner = d.get('data', {})
            if inner is True: break

            if inner.get('node_completed'):
                node_index += 1
                t = inner.get('node_type', '?')
                oid = inner.get('node_id', '?')
                out = inner.get('output', {})

                print(f"{SEP}")
                print(f"  [{node_index}] {t}")
                print(f"  ID: {oid}")
                print(f"{SEP}")

                # --- 根据输出格式打印 ---
                if isinstance(out, list):
                    for idx, item in enumerate(out):
                        if isinstance(item, dict):
                            content = item.get('content', '')
                            reasoning = item.get('reasoning_content', '')
                            if content:
                                print(f"  [content]")
                                print(f"  {content}")
                            if reasoning:
                                print(f"\n  [reasoning_content]")
                                print(f"  {reasoning}")
                elif isinstance(out, dict):
                    if out.get('status') == 'streaming':
                        print(f"  (流式输出节点，内容在下游实时传输)")
                    else:
                        content = out.get('content', '')
                        reasoning = out.get('reasoning_content', '')
                        if content:
                            # 可能是 DataFrame row
                            if hasattr(content, 'values'):
                                content = str(content.values)
                            print(f"  [content]")
                            print(f"  {content}")
                        if reasoning:
                            print(f"\n  [reasoning_content]")
                            print(f"  {reasoning}")
                print()
                continue

            answer = inner.get('answer', '')
            if answer and not inner.get('running_status'):
                # 累积最终答案的流式输出
                final_answer = (final_answer or '') + answer
                if inner.get('reasoning_content'):
                    final_reasoning = inner.get('reasoning_content', '')
                if inner.get('reference'):
                    final_ref = inner.get('reference', [])

# --- 最终答案 ---
print(f"{SEP}")
print(f"  [最终答案]")
print(f"{SEP}")
if final_reasoning:
    print(f"\n  >>> 推理过程 (reasoning_content):")
    print(f"  {final_reasoning}\n")
print(f"  >>> 回答 (content):")
print(f"  {final_answer}")
print()
