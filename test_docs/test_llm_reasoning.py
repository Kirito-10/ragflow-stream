import sys, re
sys.path.insert(0, '/ragflow')
from api.db.services.llm_service import LLMBundle
from api.db import LLMType

mdl = LLMBundle('65eefe5e659111f19e94a6b8be4f66ea', LLMType.CHAT, 'deepseek-reasoner@DeepSeek')
full = ''
count = 0
for ans in mdl.chat_streamly('', [{'role': 'user', 'content': '1+1=?'}], {'max_tokens': 50}):
    count += 1
    full = ans
    if count <= 5:
        print(f'Accum[{count}]: {ans[:120]}')

print(f'\nChunks: {count}')
print(f'Has <think>: {"<think>" in full}')

m = re.search(r'<think>(.*?)</think>', full, re.DOTALL)
if m:
    print(f'Regex match OK: {m.group(1)[:200]}')
else:
    print('NO regex match')
print(f'Full ({len(full)}): {full[:300]}')

mdl._extract_and_save_reasoning(full)
rc = mdl.get_reasoning_content()
print(f'\nget_reasoning_content length: {len(rc)}')
print(f'reasoning_content: {rc[:200]}')
