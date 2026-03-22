import requests
import json
from config import Config
import typing

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
        }
    def stream_chat(self,messages,thinking=False,temperature=0.7) -> typing.Generator[dict, None, None]:
        """
        向DeepSeek API发送流式消息
        
        Args:
            message (str): 用户发送的消息
            temperature(float): temperature设置
            
        Yields:
            dict: 流式响应数据块
        """
        
        """
            返回格式示例：
            {
                "success": True
                "done": False
                "reasoning": True
                "message_delta": "Hmm..."
            }
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
            # "max_tokens": self.max_token  TODO:最大token实现
        }
        try:
            request_result=requests.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                stream=True
            )   # 发送请求
            request_result.raise_for_status()
            for line in request_result.iter_lines():
                if line:
                    line=line.decode("utf-8")
                    if line.startswith("data:"):
                        data=line[5:].strip()
                        if data=="[DONE]":
                            # 解析完毕
                            yield {
                                "success": True,
                                "done": True,
                                "reasoning": False,
                                "message_delta": ""
                            }
                            continue
                        if data:
                            try:
                                chunk=json.loads(data)
                            except Exception:
                                # 处理json解析失败
                                print(f"跳过无法解析的块:{data}")
                                continue
                            if isinstance(chunk, dict) and 'choices' in chunk and len(chunk['choices']) > 0:
                                # 是否思考均需要的解析
                                delta = chunk['choices'][0].get('delta', {}) or {}
                                if thinking and delta["reasoning_content"] is not None and delta["content"] is None:
                                    # 思考开启，且返回思考内容
                                    delta_reasoning = delta["reasoning_content"]
                                    yield {
                                        "success": True,
                                        "done": False,
                                        "reasoning": True,
                                        "message_delta": delta_reasoning
                                    }
                                elif thinking and delta["reasoning_content"] is None and delta["content"] is not None:
                                    # 思考开启，且返回结果内容
                                    delta_message = delta["content"]
                                    yield {
                                        "success": True,
                                        "done": False,
                                        "reasoning": False,
                                        "message_delta": delta_message
                                    }
                                elif not thinking and delta["content"] is not None:
                                    # 思考关闭，返回结果内容
                                    delta_message = delta["content"]
                                    yield {
                                        "success": True,
                                        "done": False,
                                        "reasoning": False,
                                        "message_delta": delta_message
                                    }
                                else:
                                    # 这他妈是什么东西
                                    print(f"解析失败:delta:{delta}")
                                    continue
                            else:
                                print(f"跳过非返回文字内容:{chunk}")
                                continue
                            
                                                        
        except requests.exceptions.RequestException as e:
            # 处理HTTP请求错误
            yield {
                "success": False,
                "message": f"API请求错误:{str(e)}",
                "done": True
            }