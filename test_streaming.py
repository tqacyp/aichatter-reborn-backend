#!/usr/bin/env python3
"""
测试流式响应功能
这个测试需要运行中的Flask服务器
用法：先启动服务器，然后运行此测试
"""

import requests
import json
import sys

def test_streaming():
    # 1. 创建新对话
    print("1. 创建新对话...")
    response = requests.post(
        "http://127.0.0.1:5000/api/newsession",
        json={"timestamp": 12345}
    )

    if response.status_code != 200:
        print(f"创建对话失败: {response.status_code}")
        print(response.text)
        return False

    conversation_id = response.json()["uuid"]
    print(f"对话ID: {conversation_id}")

    # 2. 发送消息并处理流式响应
    print("\n2. 发送消息并处理流式响应...")
    response = requests.post(
        "http://127.0.0.1:5000/api/send",
        json={
            "conversation_id": conversation_id,
            "message": "你好，请简单介绍一下你自己",
            "thinking": False
        },
        stream=True
    )

    if response.status_code != 200:
        print(f"发送消息失败: {response.status_code}")
        print(response.text)
        return False

    print("开始接收流式响应:")

    assistant_content = ""
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:].strip()
                if data_str:
                    try:
                        data = json.loads(data_str)
                        if data.get('done'):
                            print("流结束")
                            break
                        elif data.get('success') is False:
                            print(f"错误: {data.get('message')}")
                            return False
                        else:
                            if data.get('reasoning'):
                                print(f"[思考] {data.get('message_delta', '')}", end='')
                            else:
                                delta = data.get('message_delta', '')
                                assistant_content += delta
                                print(delta, end='')
                                sys.stdout.flush()
                    except json.JSONDecodeError as e:
                        print(f"JSON解析错误: {e}")
                        print(f"原始数据: {data_str}")

    print(f"\n\n助手完整回复: {assistant_content}")

    # 3. 测试思考模式
    print("\n3. 测试思考模式...")
    response = requests.post(
        "http://127.0.0.1:5000/api/send",
        json={
            "conversation_id": conversation_id,
            "message": "1+1等于多少？",
            "thinking": True
        },
        stream=True
    )

    if response.status_code != 200:
        print(f"思考模式测试失败: {response.status_code}")
        return False

    print("思考模式响应:")
    reasoning_content = ""
    assistant_content = ""

    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:].strip()
                if data_str:
                    try:
                        data = json.loads(data_str)
                        if data.get('done'):
                            break
                        elif data.get('reasoning'):
                            reasoning_content += data.get('message_delta', '')
                            print(f"[思考] {data.get('message_delta', '')}", end='')
                        else:
                            assistant_content += data.get('message_delta', '')
                            print(f"[回复] {data.get('message_delta', '')}", end='')
                    except:
                        pass

    print(f"\n思考内容: {reasoning_content}")
    print(f"最终回复: {assistant_content}")

    return True

if __name__ == "__main__":
    print("流式响应功能测试")
    print("=" * 50)

    try:
        success = test_streaming()
        if success:
            print("\n✓ 所有测试通过!")
        else:
            print("\n✗ 测试失败")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("无法连接到服务器，请先启动Flask应用:")
        print("  cd backend && python app.py")
        sys.exit(1)
    except Exception as e:
        print(f"测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)