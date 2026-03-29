#!/usr/bin/env python3
import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from app import app

class TestSendMessage(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_send_message_missing_params(self):
        """测试缺少必要参数"""
        # 测试空JSON
        response = self.app.post('/api/send', json={})
        self.assertEqual(response.status_code, 400)

        # 测试缺少conversation_id
        response = self.app.post('/api/send', json={'message': 'Hello'})
        self.assertEqual(response.status_code, 400)

        # 测试缺少message
        response = self.app.post('/api/send', json={'conversation_id': 'test-id'})
        self.assertEqual(response.status_code, 400)

    def test_send_message_invalid_conversation(self):
        """测试无效对话ID"""
        response = self.app.post('/api/send', json={
            'conversation_id': '00000000-0000-0000-0000-000000000000',
            'message': 'Hello'
        })
        self.assertEqual(response.status_code, 404)

    def test_send_message_success_mock(self):
        """测试成功发送消息（模拟API响应）"""
        # 先创建新对话
        response = self.app.post('/api/newsession')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        conversation_id = data['uuid']

        # 模拟API响应
        mock_response_chunks = [
            'data: {"success": True, "done": False, "reasoning": False, "message_delta": "Hello"}\n\n',
            'data: {"success": True, "done": False, "reasoning": False, "message_delta": " there!"}\n\n',
            'data: {"success": True, "done": True, "reasoning": False, "message_delta": ""}\n\n'
        ]

        with patch('communications.send_response_to_frontend') as mock_send:
            # 设置模拟返回生成器
            mock_send.return_value = iter(mock_response_chunks)

            # 发送消息
            response = self.app.post('/api/send', json={
                'conversation_id': conversation_id,
                'message': 'Hi',
                'thinking': False
            })

            self.assertEqual(response.status_code, 200)
            result = json.loads(response.data)
            self.assertTrue(result['success'])
            self.assertEqual(result['conversation_id'], conversation_id)
            self.assertEqual(result['assistant_message'], 'Hello there!')

            # 验证消息是否保存到数据库
            # 这里可以添加数据库验证

    def test_send_message_with_thinking_mock(self):
        """测试思考模式（模拟API响应）"""
        # 先创建新对话
        response = self.app.post('/api/newsession')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        conversation_id = data['uuid']

        # 模拟思考模式响应
        mock_response_chunks = [
            'data: {"success": True, "done": False, "reasoning": True, "message_delta": "Let me think..."}\n\n',
            'data: {"success": True, "done": False, "reasoning": True, "message_delta": " about this."}\n\n',
            'data: {"success": True, "done": False, "reasoning": False, "message_delta": "I understand."}\n\n',
            'data: {"success": True, "done": True, "reasoning": False, "message_delta": ""}\n\n'
        ]

        with patch('communications.send_response_to_frontend') as mock_send:
            mock_send.return_value = iter(mock_response_chunks)

            response = self.app.post('/api/send', json={
                'conversation_id': conversation_id,
                'message': 'Explain something',
                'thinking': True
            })

            self.assertEqual(response.status_code, 200)
            result = json.loads(response.data)
            self.assertTrue(result['success'])
            # 思考内容不应该包含在最终消息中
            self.assertEqual(result['assistant_message'], 'I understand.')

    def test_send_message_api_error(self):
        """测试API错误情况"""
        # 先创建新对话
        response = self.app.post('/api/newsession')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        conversation_id = data['uuid']

        with patch('communications.send_response_to_frontend') as mock_send:
            # 模拟API异常
            mock_send.side_effect = Exception("API connection failed")

            response = self.app.post('/api/send', json={
                'conversation_id': conversation_id,
                'message': 'Hi'
            })

            # 应该返回500错误
            self.assertEqual(response.status_code, 500)

if __name__ == '__main__':
    # 清理可能存在的测试数据库
    test_db = os.path.join(os.path.dirname(__file__), "test_messages.db")
    if os.path.exists(test_db):
        os.remove(test_db)

    # 运行测试
    unittest.main()