#!/usr/bin/env python3
import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from app import app

# 使用测试客户端
client = app.test_client()

# 测试1: 创建新对话
print("测试1: 创建新对话")
response = client.post('/api/newsession',
                       data=json.dumps({'timestamp': 12345}),
                       content_type='application/json')
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    data = json.loads(response.data)
    print(f"响应: {data}")
    conversation_id = data['uuid']
else:
    print(f"错误: {response.data}")
    sys.exit(1)

# 测试2: 发送消息（模拟API）
print("\n测试2: 发送消息")
# 模拟API响应
import communications
from unittest.mock import patch

mock_response = [
    'data: {"success": True, "done": False, "reasoning": False, "message_delta": "Hello"}\n\n',
    'data: {"success": True, "done": False, "reasoning": False, "message_delta": " there!"}\n\n',
    'data: {"success": True, "done": True, "reasoning": False, "message_delta": ""}\n\n'
]

with patch('communications.send_response_to_frontend') as mock_send:
    mock_send.return_value = iter(mock_response)

    response = client.post('/api/send',
                          data=json.dumps({
                              'conversation_id': conversation_id,
                              'message': 'Hi',
                              'thinking': False
                          }),
                          content_type='application/json')

    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = json.loads(response.data)
        print(f"响应: {data}")
        print(f"助手回复: {data.get('assistant_message')}")
    else:
        print(f"错误: {response.data}")

print("\n测试完成")