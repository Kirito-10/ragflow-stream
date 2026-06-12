import requests, json

h = {'Authorization': 'Bearer ragflow-Y1NTMwMTEyNjVhYTExZjFiYmI2MTJlOG'}
# Get the DSL from the agents list
r = requests.get('http://localhost:9380/api/v1/agents', headers=h)
d = r.json()
for a in d.get('data', []):
    if a.get('id') == '6a6916d265ae11f189a6e676ff3a315b':
        dsl = a.get('dsl', {})
        if isinstance(dsl, str):
            dsl = json.loads(dsl)
        print('=== Canvas State ===')
        print('Path:', json.dumps(dsl.get('path', []), ensure_ascii=False))
        print('Answer:', json.dumps(dsl.get('answer', []), ensure_ascii=False))
        print('History length:', len(dsl.get('history', [])))
        print('Messages length:', len(dsl.get('messages', [])))
        print()

        # Check if answer component in components
        for k in dsl.get('components', {}):
            if 'Answer' in k:
                ans_obj = dsl['components'][k].get('obj', {})
                has_output = bool(ans_obj.get("output"))
                has_inputs = bool(ans_obj.get("inputs"))
                print(f'{k}: output={has_output}, inputs={has_inputs}')
        break

# Also check the latest conversation
r2 = requests.get('http://localhost:9380/api/v1/agents/6a6916d265ae11f189a6e676ff3a315b/sessions', headers=h)
d2 = r2.json()
print('\n=== Sessions ===')
sessions = d2.get('data', [])
if isinstance(sessions, dict):
    sessions = sessions.get('items', [sessions])
for s in (sessions if isinstance(sessions, list) else [sessions]):
    sid = s.get('id', '?')
    dsl = s.get('dsl', {})
    if isinstance(dsl, str):
        dsl = json.loads(dsl)
    print(f'Session: {sid}')
    print(f'  Path: {json.dumps(dsl.get("path",[]), ensure_ascii=False)}')
    print(f'  Answer: {json.dumps(dsl.get("answer",[]), ensure_ascii=False)}')
    print(f'  Messages len: {len(dsl.get("messages",[]))}')
