import requests, json

h = {'Authorization': 'Bearer ragflow-Y1NTMwMTEyNjVhYTExZjFiYmI2MTJlOG'}
workflow_id = '6a6916d265ae11f189a6e676ff3a315b'

r = requests.get(f'http://localhost:9380/api/v1/canvas/get/{workflow_id}', headers=h)
d = r.json()
print(json.dumps(d, indent=2, ensure_ascii=False)[:3000])

if d.get('code') == 0:
    dsl = d['data'].get('dsl', {})
    if isinstance(dsl, str):
        dsl = json.loads(dsl)
    print('\n=== Components ===')
    for k, v in dsl.get('components', {}).items():
        ds = v.get('downstream', [])
        pid = v.get('parent_id', '')
        print(f"  {v.get('component_name', '?')}: {k}  downstream: {ds}  parent_id: {pid}")
        params = v.get('params', {})
        for pk, pv in params.items():
            print(f"    param {pk}: {json.dumps(pv, ensure_ascii=False)[:100]}")
    
    print('\n=== Paths ===')
    for i, p in enumerate(dsl.get('path', [])):
        print(f"  Path {i}: {p}")
    
    print('\n=== Messages ===')
    for i, m in enumerate(dsl.get('messages', [])):
        print(f"  Msg {i}: {json.dumps(m, ensure_ascii=False)[:200]}")

# Also check the embedding endpoint
r2 = requests.get(f'http://localhost:9380/api/v1/agents/{workflow_id}', headers=h)
print('\n=== Agent info ===')
d2 = r2.json()
print(json.dumps(d2, indent=2, ensure_ascii=False)[:2000])
