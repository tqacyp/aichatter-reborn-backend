import requests
import json
from config import Config
import typing


class DeepSeekAPI:
    """
    模块化设计，api.py只负责发送完整上下文内容到api.deepseek.com，对话历史由app.py维护。
    """

    # 官方文档允许的思考强度取值（medium/xhigh 会被映射为 high）
    ALLOWED_REASONING_EFFORTS = {"low", "medium", "high", "xhigh", "max"}

    def __init__(self) -> None:
        self.api_key = Config.DEEPSEEK_API_KEY
        self.api_url = Config.DEEPSEEK_API_URL
        self.model = Config.MODEL
        self.max_token = Config.MAX_TOKEN
        self.reasoning_effort = self._normalize_effort(Config.REASONING_EFFORT)
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _normalize_effort(self, effort):
        """校验 config 中的 reasoning_effort，非法值回退为官方默认 high 并打印警告"""
        value = (effort or "").strip().lower()
        if value in self.ALLOWED_REASONING_EFFORTS:
            return value
        print(f"警告: 无效的 REASONING_EFFORT 配置 '{effort}'，已回退为默认值 'high'")
        return "high"

    def stream_chat(self, messages, thinking=False, temperature=0.7, cancel_event=None) -> typing.Generator[dict, None, None]:
        """
        向DeepSeek API发送流式消息

        请求体（官方文档 OpenAI 格式）:
            model:            Config.MODEL（统一 deepseek-v4-flash）
            thinking:         {"type": "enabled"/"disabled"} 思考模式开关
            reasoning_effort: Config.REASONING_EFFORT 思考强度 (low/medium/high/xhigh/max)

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

        # 思考开关（OpenAI 格式顶层参数）:
        #   {"thinking": {"type": "enabled"/"disabled"}}
        thinking_type = "enabled" if thinking else "disabled"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "thinking": {"type": thinking_type},
            # 思考强度控制（OpenAI 格式顶层参数 reasoning_effort），在 config.py 中配置
            "reasoning_effort": self.reasoning_effort,
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
