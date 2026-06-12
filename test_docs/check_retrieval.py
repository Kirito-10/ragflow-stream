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

print('Session:', sid[:30])

# Step 2
r2 = requests.post(url, headers=h, json={
    'question': '请根据环保法规，列出二氧化硫(SO2)排放限值。',
    'session_id': sid, 'stream': True
}, stream=True, timeout=180)

buf = ''
nodes = []
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
                nodes.append({
                    'type': inner.get('node_type'),
                    'id': inner.get('node_id', ''),
                    'output': inner.get('output', {})
                })

print()
for n in nodes:
    out = n['output']
    print(f"node_completed: type={n['type']}  id={n['id'][:40]}")
    out_str = json.dumps(out, ensure_ascii=False)
    if out_str == '{}':
        print('  output: (empty)')
    else:
        print(f'  output: {out_str[:400]}')

if not any('Retrieval' in n['type'] or 'Retrieval' in n['id'] for n in nodes):
    print('\n>>> Retrieval 节点未产生 node_completed 事件')
    print('>>> 可能原因: 知识库文档解析失败，chunks 未入库')
