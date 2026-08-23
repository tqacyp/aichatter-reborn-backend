import requests
import json
from config import Config
import typing


class DeepSeekAPI:
    """
    模块化设计，api.py只负责发送完整上下文内容到api.deepseek.com，对话历史由app.py维护。
    """

    def __init__(self) -> None:
        self.api_key = Config.DEEPSEEK_API_KEY
        self.api_url = Config.DEEPSEEK_API_URL
        self.model_thinking = Config.MODEL_THINKING
        self.model_not_thinking = Config.MODEL_NOT_THINKING
        self.max_token = Config.MAX_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def stream_chat(self, messages, thinking=False, temperature=0.7, cancel_event=None) -> typing.Generator[dict, None, None]:
        """
        向DeepSeek API发送流式消息

        Args:
            messages: 完整消息上下文
            thinking: 是否开启思考模式
            temperature: temperature 设置
            cancel_event: 可选的 threading.Event，置位后会在下一个数据块处停止生成

        Yields:
            dict: 流式响应数据块，格式为
            {"success": True, "done": False, "reasoning": False, "message_delta": "..."}
        """
        if messages is None:
            raise ValueError("Messages can't be empty")

        if thinking:
            model_name = self.model_thinking
            thinking_enabled = "enabled"
        else:
            model_name = self.model_not_thinking
            thinking_enabled = "disabled"

        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "thinking": {"type": thinking_enabled},
            # "max_tokens": self.max_token  TODO:最大token实现
        }

        def done_chunk(cancelled=False):
            return {
                "success": True,
                "done": True,
                "cancelled": cancelled,
                "reasoning": False,
                "message_delta": ""
            }

        try:
            request_result = requests.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                stream=True,
                timeout=Config.REQUEST_TIMEOUT
            )
            request_result.raise_for_status()
            try:
                for line in request_result.iter_lines():
                    if cancel_event is not None and cancel_event.is_set():
                        # 用户点了停止：给前端发一个正常的结束标记，
                        # app.py 会保存已经生成的部分内容。
                        yield done_chunk(cancelled=True)
                        return

                    if not line:
                        continue

                    line = line.decode("utf-8")
                    if not line.startswith("data:"):
                        continue

                    data = line[5:].strip()
                    if data == "[DONE]":
                        yield done_chunk()
                        return

                    if not data:
                        continue

                    try:
                        chunk = json.loads(data)
                    except Exception:
                        print(f"跳过无法解析的块:{data}")
                        continue

                    if not (isinstance(chunk, dict) and 'choices' in chunk and len(chunk['choices']) > 0):
                        continue

                    delta = chunk['choices'][0].get('delta', {}) or {}
                    reasoning_delta = delta.get('reasoning_content')
                    content_delta = delta.get('content')

                    if thinking and reasoning_delta:
                        yield {
                            "success": True,
                            "done": False,
                            "reasoning": True,
                            "message_delta": reasoning_delta
                        }
                    elif content_delta:
                        yield {
                            "success": True,
                            "done": False,
                            "reasoning": False,
                            "message_delta": content_delta
                        }

                # 上游没有发送 [DONE] 时，补一个结束标记，避免前端误报“连接意外结束”
                yield done_chunk()
            finally:
                request_result.close()

        except requests.exceptions.RequestException as e:
            yield {
                "success": False,
                "message": f"API请求错误:{str(e)}",
                "done": True
            }
