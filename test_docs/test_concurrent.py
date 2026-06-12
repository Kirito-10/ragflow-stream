"""并发测试：同时调用 test 和 test2 Agent"""
import requests, json, threading, time

h = {'Authorization': 'Bearer ragflow-Y1NTMwMTEyNjVhYTExZjFiYmI2MTJlOG'}
BASE = 'http://localhost:9380'
TEST_ID = '02c3e74e659211f1b654a6b8be4f66ea'
TEST2_ID = '6a6916d265ae11f189a6e676ff3a315b'

results = {}
lock = threading.Lock()

def run_agent(name, agent_id, question, files=None):
    """Run one agent session end-to-end."""
    t0 = time.time()
    try:
        # Create session
        if files:
            with open(files, 'rb') as f:
                r = requests.post(f'{BASE}/api/v1/agents/{agent_id}/sessions',
                                  headers=h,
                                  files={'License': (os.path.basename(files), f, 'text/plain')},
                                  timeout=180)
        else:
            r = requests.post(f'{BASE}/api/v1/agents/{agent_id}/completions',
                              headers={**h, 'Content-Type': 'application/json'},
                              json={'question': '', 'stream': True},
                              stream=True, timeout=180)
            sid = None
            buf = ''
            for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                buf += chunk
                while '\n\n' in buf:
                    line, buf = buf.split('\n\n', 1)
                    if line.startswith('data:'):
                        d = json.loads(line[5:])
                        if d.get('data') is True: break
                        inner = d['data']
                        if 'session_id' in inner:
                            sid = inner['session_id']
                            break
                if sid: break
            if not sid:
                with lock: results[name] = {'error': 'no session_id'}
                return

        # If files case, get sid from response
        if files:
            sid = r.json()['data']['id']

        # Ask question
        r2 = requests.post(f'{BASE}/api/v1/agents/{agent_id}/completions',
                           headers={**h, 'Content-Type': 'application/json'},
                           json={'question': question, 'session_id': sid, 'stream': True, 'sync_dsl': True},
                           stream=True, timeout=300)

        nodes = []
        final_answer = ''
        for line in r2.iter_lines(decode_unicode=True):
            if line.startswith('data:'):
                d = json.loads(line[5:])
                if d.get('data') is True: break
                inner = d['data']
                if inner.get('node_completed'):
                    nodes.append(inner.get('node_type'))
                if inner.get('answer') and not inner.get('running_status'):
                    final_answer = inner['answer']

        elapsed = time.time() - t0
        with lock:
            results[name] = {
                'elapsed': f'{elapsed:.1f}s',
                'nodes': nodes,
                'answer_len': len(final_answer),
                'answer_preview': final_answer[:100]
            }
    except Exception as e:
        with lock:
            results[name] = {'error': str(e)}

import os

# Run test and test2 concurrently
threads = []
for label, aid, q, f in [
    ('test (对话)', TEST_ID, '请根据环保法规，列出SO2排放限值', None),
    ('test2 (文件上传)', TEST2_ID, '请审核这份报告', os.path.join(os.path.dirname(__file__), '环评报告_模拟.txt')),
]:
    t = threading.Thread(target=run_agent, args=(label, aid, q, f))
    threads.append(t)
    t.start()

print(f'启动 {len(threads)} 个并发请求，等待完成...\n')

for t in threads:
    t.join()

print('=' * 60)
print('  并发测试结果')
print('=' * 60)
for name, r in results.items():
    print(f'\n  {name}:')
    if 'error' in r:
        print(f'    ERROR: {r["error"]}')
    else:
        print(f'    耗时: {r["elapsed"]}')
        print(f'    节点: {len(r["nodes"])} 个 → {r["nodes"]}')
        print(f'    答案: {r["answer_len"]} 字符')
        print(f'    预览: {r["answer_preview"][:80]}...' if r['answer_preview'] else '    (空)')
print()
