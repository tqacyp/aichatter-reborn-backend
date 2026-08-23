import json
from api import DeepSeekAPI


def send_response_to_frontend(content: list[dict], is_thinking: bool, cancel_event=None):
    """向前端发送 SSE 格式的流式数据。

    Args:
        content: app.py 组装好的完整消息上下文
        is_thinking: 是否开启思考模式
        cancel_event: 可选的停止事件
    """
    deepseek_api = DeepSeekAPI()
    response = deepseek_api.stream_chat(content, is_thinking, cancel_event=cancel_event)
    for value in response:
        yield f"data: {json.dumps(value, ensure_ascii=False)}\n\n"
