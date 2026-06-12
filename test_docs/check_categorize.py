import requests, json

url = 'http://localhost:9380/api/v1/agents/02c3e74e659211f1b654a6b8be4f66ea/completions'
h = {'Authorization': 'Bearer ragflow-Y1NTMwMTEyNjVhYTExZjFiYmI2MTJlOG', 'Content-Type': 'application/json'}

# Step 1
r1 = requests.post(url, headers=h, json={'question': '', 'stream': True}, stream=True, timeout=30)
buf = ''
sid = None
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

# Step 2
r2 = requests.post(url, headers=h, json={
    'question': '请根据环保法规，列出二氧化硫(SO2)排放限值。',
    'session_id': sid, 'stream': True, 'sync_dsl': True
}, stream=True, timeout=180)

buf = ''
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
                t = inner.get('node_type')
                out = inner.get('output', {})
                print(f'\n=== node_completed: {t} ===')
                print(f'output keys: {list(out.keys()) if isinstance(out, dict) else "list/other"}')
                out_str = json.dumps(out, ensure_ascii=False)
                if len(out_str) > 600:
                    print(f'output[:600]: {out_str[:600]}')
                else:
                    print(f'output: {out_str}')
                
                # Check for reasoning_content in output
                if isinstance(out, dict):
                    rc = out.get('reasoning_content', '')
                elif isinstance(out, list) and len(out) > 0:
                    rc = out[0].get('reasoning_content', '') if isinstance(out[0], dict) else ''
                else:
                    rc = ''
                if rc:
                    print(f'>>> reasoning_content: {rc[:300]}')
                else:
                    print(f'>>> reasoning_content: (empty)')
