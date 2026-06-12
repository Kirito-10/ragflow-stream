"""直接测试 DeepSeek API 是否返回 reasoning_content"""
import requests, json, os

# Read API key from the container's env or check config
# First: check what API key ragflow uses for DeepSeek
import subprocess
result = subprocess.run(
    'docker exec ragflow-server python -c "from api.db.services.user_service import TenantLLMService; '
    'import json; '
    'mdls = TenantLLMService.get_my_llms(tenant_id=\"0\"); '
    'print([m for m in mdls if \"deepseek\" in m.get(\"llm_name\",\"\").lower()])"',
    capture_output=True, text=True, shell=True
)
print("DeepSeek models in RAGFlow:")
print(result.stdout[:500])
print(result.stderr[:500])

# Now test directly with a known API key
# The deepseek-reasoner model from the workflow
import openai

# Read the API key from the docker container
result2 = subprocess.run(
    'docker exec ragflow-server python -c "'
    'from api.db.db_models import TenantLLM; '
    'from api.db import LLMType; '
    'mdl = TenantLLM.select().where(TenantLLM.llm_factory == \'DeepSeek\', TenantLLM.llm_type == \'chat\').first(); '
    'print(mdl.api_key[:10] + \'...\' if mdl else \'NOT FOUND\')"',
    capture_output=True, text=True, shell=True
)
print(f"\nDeepSeek API key prefix: {result2.stdout.strip()}")
print(f"Error: {result2.stderr.strip()[:200]}")

# Try to get the actual API key and test directly
print("\n=== Direct API Test ===")
result3 = subprocess.run(
    'docker exec ragflow-server python -c "'
    'from api.db.db_models import TenantLLM; '
    'mdl = TenantLLM.select().where(TenantLLM.llm_factory == \'DeepSeek\', TenantLLM.llm_type == \'chat\').first(); '
    'print(mdl.api_key if mdl else \'\')"',
    capture_output=True, text=True, shell=True
)
api_key = result3.stdout.strip()
if not api_key:
    print("ERROR: Could not find DeepSeek API key")
    exit(1)

print(f"API key: {api_key[:10]}...")

client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

print("\nCalling deepseek-reasoner with reasoning_content check...")
response = client.chat.completions.create(
    model="deepseek-reasoner",
    messages=[{"role": "user", "content": "1+1=?"}],
    stream=True,
    max_tokens=100,
)

reasoning_chunks = 0
content_chunks = 0
for chunk in response:
    delta = chunk.choices[0].delta if chunk.choices else None
    if not delta:
        continue
    rc = getattr(delta, "reasoning_content", None)
    ct = getattr(delta, "content", None)
    if rc:
        reasoning_chunks += 1
        if reasoning_chunks <= 3:
            print(f"  REASONING[{reasoning_chunks}]: {rc[:80]}")
    if ct:
        content_chunks += 1
        if content_chunks <= 3:
            print(f"  CONTENT[{content_chunks}]: {ct[:80]}")

print(f"\nTotal: {reasoning_chunks} reasoning chunks, {content_chunks} content chunks")
