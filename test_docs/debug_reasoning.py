"""Debug reasoning_content flow through Generate node."""
import json, requests

h = {'Authorization': 'Bearer ragflow-Y1NTMwMTEyNjVhYTExZjFiYmI2MTJlOG'}

# Step 1: Check that deepseek-reasoner returns reasoning_content
print("=== Step 1: Direct DeepSeek API check ===")
r = requests.get('http://localhost:9380/api/v1/agents', headers=h)
for a in r.json()['data']:
    if a['id'] == '6a6916d265ae11f189a6e676ff3a315b':
        dsl = json.loads(a['dsl']) if isinstance(a['dsl'], str) else a['dsl']
        for k, v in dsl['components'].items():
            if 'Generate' in k:
                llm_id = v['obj'].get('params', {}).get('llm_id', '?')
                print(f'  {k}: llm_id={llm_id}')
        break

# Step 2: Do a live test with verbose logging inside the Docker container
print("\n=== Step 2: Check internal /v1/canvas/completion ===")
with open(r'D:\game\first\ragflow-code\test_docs\环评报告_模拟.txt', 'rb') as f:
    r = requests.post(
        'http://localhost:9380/api/v1/agents/6a6916d265ae11f189a6e676ff3a315b/sessions',
        headers=h,
        files={'License': ('环评报告_模拟.txt', f, 'text/plain')},
        timeout=120,
    )
sid = r.json()['data']['id']
print(f'  session: {sid[:24]}...')

r2 = requests.post(
    'http://localhost:9380/api/v1/agents/6a6916d265ae11f189a6e676ff3a315b/completions',
    headers={**h, 'Content-Type': 'application/json'},
    json={'question': '请审核', 'session_id': sid, 'stream': True, 'sync_dsl': True},
    stream=True,
    timeout=300,
)

events = []
for line in r2.iter_lines(decode_unicode=True):
    if not line or not line.startswith('data:'):
        continue
    d = json.loads(line[5:])
    if d.get('data') is True:
        break
    inner = d['data']
    if inner.get('node_completed'):
        t = inner.get('node_type')
        out = inner.get('output', {})
        print(f'\n  node:{t} output_keys={list(out[0].keys()) if isinstance(out, list) and out else "N/A"}')
        if isinstance(out, list) and out:
            rc = out[0].get('reasoning_content', 'NOT_FOUND')
            print(f'    reasoning_content present: {bool(rc)}')
            if rc:
                print(f'    reasoning_content[:200]: {str(rc)[:200]}')
    if inner.get('answer') and not inner.get('running_status'):
        rc = inner.get('reasoning_content', 'NOT_IN_KEY')
        print(f'\n  final answer: reasoning_content={rc[:100] if rc else "empty"}')
        
print('\nDone.')
