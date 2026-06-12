import requests, json

h = {'Authorization': 'Bearer ragflow-Y1NTMwMTEyNjVhYTExZjFiYmI2MTJlOG'}
url = 'http://localhost:9380/api/v1/agents/02c3e74e659211f1b654a6b8be4f66ea/completions'

# Step 1: create session
r1 = requests.post(url, headers={**h, 'Content-Type': 'application/json'},
                   json={'question': '', 'stream': True}, stream=True, timeout=180)
sid = None
buf = ''
for chunk in r1.iter_content(chunk_size=None, decode_unicode=True):
    buf += chunk
    if 'data:' in buf and '\n\n' in buf:
        for line in buf.split('\n\n'):
            if line.startswith('data:'):
                d = json.loads(line[5:])
                inner = d.get('data', {})
                if 'session_id' in inner:
                    sid = inner['session_id']
                    break
    if sid:
        break
print(f'Session: {sid}')

# Step 2: ask question
r2 = requests.post(url, headers={**h, 'Content-Type': 'application/json'},
                   json={'question': '请根据环保法规，列出SO2排放限值', 'session_id': sid,
                         'stream': True, 'sync_dsl': True},
                   stream=True, timeout=300)

for line in r2.iter_lines(decode_unicode=True):
    if line.startswith('data:'):
        d = json.loads(line[5:])
        if d.get('data') is True:
            break
        inner = d['data']
        nc = inner.get('node_completed')
        rs = inner.get('running_status')
        ans = inner.get('answer', '')
        if nc:
            nt = inner.get('node_type')
            nid = inner.get('node_id', '')
            print(f'\nNODE: type={nt} id={nid[:30]}')
            out = inner.get('output', {})
            if isinstance(out, list) and out:
                keys = list(out[0].keys())
                rc = out[0].get('reasoning_content', 'N/A')
                print(f'  output_keys={keys} rc_len={len(str(rc))}')
                if rc and rc != 'N/A':
                    print(f'  rc[:100]: {str(rc)[:100]}')
        elif rs and ans:
            print(f'PROGRESS: {ans[:80]}')
        elif ans:
            print(f'ANSWER_CHUNK: {ans[:100]}')
print('DONE')
