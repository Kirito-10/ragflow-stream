import requests, json

# Login
resp = requests.post('http://localhost:9380/api/v1/user/login', 
    json={'email':'louiswui@126.com','password':'123456aa'})
print('Login:', resp.json().get('code'))
token = resp.cookies.get('session')

# List canvases
resp2 = requests.get('http://localhost:9380/api/v1/canvas/list', cookies={'session': token})
data = resp2.json()
if data.get('code') == 0:
    for c in data['data']:
        print(f"  Canvas: id={c['id']}  title={c.get('title','?')}")
else:
    print('List error:', data)
