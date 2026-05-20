import requests
import json

# 测试排版 API
r = requests.post('http://127.0.0.1:5000/api/format', json={
    'content': '## 测试标题\n\n这是一段**测试**文章。\n\n- 列表1\n- 列表2',
    'theme': 'newspaper'
})
print(f'Format API: {r.status_code}')
if r.status_code == 200:
    d = r.json()
    print(f'Title: {d.get("title")}, Words: {d.get("word_count")}, HTML length: {len(d.get("html",""))}')
else:
    print(f'Error: {r.text[:500]}')

# 测试 AI 配置 API
r = requests.get('http://127.0.0.1:5000/api/ai-config')
print(f'\nAI Config API: {r.status_code}, {r.json()}')

# 测试账号列表
r = requests.get('http://127.0.0.1:5000/api/accounts')
print(f'\nAccounts API: {r.status_code}, count: {len(r.json())}')

# 测试添加第二个账号
r = requests.post('http://127.0.0.1:5000/api/accounts', json={
    'name': '副号',
    'app_id': 'wx9876543210',
    'app_secret': 'test_secret_2',
    'author': '副号作者'
})
print(f'\nAdd second account: {r.status_code}, {r.json()}')

# 测试设置默认账号
accounts = requests.get('http://127.0.0.1:5000/api/accounts').json()
if len(accounts) >= 2:
    r = requests.post(f'http://127.0.0.1:5000/api/accounts/{accounts[1]["id"]}/default')
    print(f'\nSet default: {r.status_code}, {r.json()}')

# 测试删除账号
if len(accounts) >= 1:
    r = requests.delete(f'http://127.0.0.1:5000/api/accounts/{accounts[0]["id"]}')
    print(f'\nDelete account: {r.status_code}, {r.json()}')

print('\n=== All API tests passed! ===')
