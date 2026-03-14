from email.mime import application
from pyexpat import model
from threading import Thread

import requests
import json
from config import Config
import config

class DeepSeekAPI:
    """
    模块化设计，api.py只负责发送完整上下文内容到api.deepseek.com,对话历史由app.py维护
    """
    def __init__(self) -> None:
        self.api_key=Config.DEEPSEEK_API_KEY
        self.api_url=Config.DEEPSEEK_API_URL
        self.model_thinking = Config.MODEL_THINKING
        self.model_not_thinking = Config.MODEL_NOT_THINKING
        self.max_token = Config.MAX_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    def stream_chat(self,messages,thinking=False,temperature=0.7):
        """
        向DeepSeek API发送流式消息
        
        Args:
            message (str): 用户发送的消息
            temperature(float): temperature设置
            
        Yields:
            dict: 流式响应数据块
        """
        if messages is None:
            raise ValueError("Messages can't be empty")
        
        if thinking:
            model_name=self.model_thinking
        else:
            model_name=self.model_not_thinking
        
        payload = {          # 请求内容
            "model": model_name,
            "messages": messages,
            "stream": True,  # 启用流式传输
            "temperature": temperature,
            "max_tokens": self.max_token
        }
        
