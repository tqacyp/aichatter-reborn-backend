class Config:
    with open("api-key.txt", "r") as f:
        DEEPSEEK_API_KEY = f.read().strip()
    DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
    # 统一模型（思考/非思考均使用同一模型）
    MODEL = "deepseek-v4-flash"
    # 思考强度控制（OpenAI 格式顶层参数 reasoning_effort）
    # 可选值: low / medium / high / xhigh / max
    # 官方映射: medium、xhigh 会映射为 high；不传时默认 high
    REASONING_EFFORT = "high"
    MAX_TOKEN = 8192
    REQUEST_TIMEOUT = (10, 120)  # (连接超时, 流式读取超时)
    SYSTEM_PROMPT = "你是一个有帮助的AI助手。请用中文回答用户的问题。"