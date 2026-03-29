class Config:
    with open("api-key.txt", "r") as f:
        DEEPSEEK_API_KEY = f.read().strip()
    DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
    MODEL_THINKING = "deepseek-reasoner"
    MODEL_NOT_THINKING = "deepseek-chat"
    MAX_TOKEN = 8192
    SYSTEM_PROMPT = "你是一个有帮助的AI助手。请用中文回答用户的问题。"