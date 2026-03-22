import requests
import json
from api import DeepSeekAPI

def send_response_to_frontend(content: list[dict],is_thinking: bool):
    """向前端发送数据

    Args:
        content (dict): 前端发来的内容经app.py处理后的dict
    Yields:
        dict: 流式响应数据块
    """
    deepseek_api = DeepSeekAPI()
    response = deepseek_api.stream_chat(content,is_thinking)
    for value in response:
        yield f"data: {json.dumps(value,ensure_ascii=False)}\n\n"