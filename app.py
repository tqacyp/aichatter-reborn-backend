from flask import Flask, abort, request, Response, stream_with_context, jsonify
from flask_cors import CORS
import sqlite3
from api import DeepSeekAPI
from datetime import datetime, timedelta
import uuid
import os
import json
import communications
import config

"""
    app.py 功能: aichatter-reborn 后端，负责处理api请求，并实现与数据库交互
"""

app = Flask(__name__)
deepseek_api = DeepSeekAPI()
DB_PATH = os.path.join(os.path.dirname(__file__),"messages.db")
SQL_PATH = os.path.join(os.path.dirname(__file__),"schema.sql")
CORS(app, origins=['http://localhost:5173','http://127.0.0.1:5173'])

def init_db():
    # 初始化SQLite3数据库
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    with open(SQL_PATH,"r",encoding='utf-8') as f:
        sql_script=f.read()
    cur.executescript(sql_script)
    conn.commit()
    print("数据库初始化完成！")
    conn.close()

def ensure_db():
    # 确保数据库和表存在
    if not os.path.exists(DB_PATH):
        init_db()
    else:
        # 检查表是否存在
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
            if not cur.fetchone():
                init_db()
        finally:
            conn.close()

def get_db():
    # 获取数据库连接
    ensure_db()
    conn = sqlite3.connect(DB_PATH)
    return conn

def load_conversation_history(conversation_id, limit=20, exclude_message_id=None):
    """加载指定对话的历史消息"""
    conn = get_db()
    cur = conn.cursor()

    if exclude_message_id:
        # 排除指定ID的消息
        cur.execute("""
            SELECT role, content
            FROM messages
            WHERE conversation_id = ? AND is_reasoning = 0 AND id != ?
            ORDER BY created_at ASC
            LIMIT ?
        """, (conversation_id, exclude_message_id, limit))
    else:
        cur.execute("""
            SELECT role, content
            FROM messages
            WHERE conversation_id = ? AND is_reasoning = 0
            ORDER BY created_at ASC
            LIMIT ?
        """, (conversation_id, limit))

    messages = []
    for row in cur.fetchall():
        messages.append({"role": row[0], "content": row[1]})

    conn.close()
    return messages

def save_message(conversation_id, message_id, role, content, is_reasoning=False):
    """保存消息到数据库（支持思考内容）"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (id, conversation_id, role, content, is_reasoning) VALUES (?, ?, ?, ?, ?)",
        (message_id, conversation_id, role, content, 1 if is_reasoning else 0)
    )
    conn.commit()
    conn.close()

def save_assistant_message(conversation_id, message_id, content):
    """保存助手回复到数据库（保持向后兼容）"""
    save_message(conversation_id, message_id, 'assistant', content, is_reasoning=False)

def save_reasoning_message(conversation_id, message_id, content):
    """保存思考内容到数据库"""
    save_message(conversation_id, message_id, 'assistant', content, is_reasoning=True)

def generate_conversation_title(user_message, assistant_reply):
    """简化版标题生成：只取用户第一句话的前几个字"""
    if user_message:
        # 1. 找到第一句话的结束位置（句号、问号、感叹号或换行）
        sentence_end_chars = ['。', '.', '？', '?', '！', '!', '\n']
        first_sentence_end = len(user_message)

        for char in sentence_end_chars:
            pos = user_message.find(char)
            if 0 < pos < first_sentence_end:
                first_sentence_end = pos + 1  # 包含结束标点

        # 2. 提取第一句话
        first_sentence = user_message[:first_sentence_end].strip()

        # 3. 只取前20个字符（8-10个汉字，根据用户偏好）
        max_title_length = 10
        if len(first_sentence) > max_title_length:
            title = first_sentence[:max_title_length]
        else:
            title = first_sentence

        # 4. 如果第一句话太短，使用简单截取
        if len(title) < 3:
            title = user_message[:10].strip() if len(user_message) >= 10 else user_message.strip()
    else:
        # 没有用户消息的情况
        title = "新对话"

    # 确保标题不为空
    if not title or len(title) < 2:
        title = "新对话"

    return title

def update_conversation_title(conversation_id, title, force_update=False):
    """更新对话标题，可选择强制更新"""
    try:
        conn = get_db()
        cur = conn.cursor()

        if not force_update:
            # 检查是否已有非默认标题
            cur.execute("SELECT title FROM conversations WHERE id = ?", (conversation_id,))
            row = cur.fetchone()
            existing_title = row[0] if row else "新对话"
            # 如果已有非默认标题，则不更新（除非强制）
            if existing_title and existing_title != "新对话":
                conn.close()
                return False

        cur.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conversation_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"更新对话标题失败: {e}")
        return False

def get_system_prompt():
    """获取系统提示词"""
    return config.Config.SYSTEM_PROMPT

def build_message_context(history_messages, current_user_message):
    """构建完整的消息上下文"""
    system_prompt = get_system_prompt()

    # 构建消息列表
    messages = [{"role": "system", "content": system_prompt}]

    # 添加历史消息
    messages.extend(history_messages)

    # 添加当前用户消息
    messages.append({"role": "user", "content": current_user_message})

    return messages

@app.route("/")
def index():
    abort(404)

@app.route("/api/newsession",methods=['POST'])
def new_session():
    # 获取前端发送的时间戳（可选）
    data = request.get_json()
    if data is None:
        abort(400, description="请求必须是JSON格式")

    timestamp = data.get('timestamp')  # 可选字段，目前未使用

    # 生成UUID
    conversation_id = str(uuid.uuid4())

    # 插入数据库
    conn = get_db()
    cur = conn.cursor()
    try:
        # 使用默认值：title='新对话', created_at=CURRENT_TIMESTAMP
        cur.execute(
            "INSERT INTO conversations (id) VALUES (?)",
            (conversation_id,)
        )
        conn.commit()
    except Exception as e:
        print(f"插入对话记录失败: {e}")
        conn.close()
        abort(500, description="数据库插入失败")
    finally:
        conn.close()

    # 返回UUID
    return jsonify({"uuid": conversation_id})

@app.route("/api/send",methods=['POST'])
def send_request():
    # 1. 验证请求数据
    data = request.get_json()
    if not data:
        abort(400, description="请求必须是JSON格式")

    conversation_id = data.get('conversation_id')
    user_message = data.get('message')
    thinking = data.get('thinking', False)

    if not conversation_id or not user_message:
        abort(400, description="缺少必要参数: conversation_id 或 message")

    # 2. 验证对话存在
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
    if not cur.fetchone():
        conn.close()
        abort(404, description="对话不存在")

    # 3. 保存用户消息（使用事务）
    user_message_id = str(uuid.uuid4())
    try:
        cur.execute(
            "INSERT INTO messages (id, conversation_id, role, content, is_reasoning) VALUES (?, ?, 'user', ?, 0)",
            (user_message_id, conversation_id, user_message)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"保存用户消息失败: {e}")
        abort(500, description="保存用户消息失败")

    # 4. 加载历史消息（排除刚保存的用户消息，避免重复）
    try:
        history_messages = load_conversation_history(conversation_id, exclude_message_id=user_message_id)
    except Exception as e:
        conn.close()
        print(f"加载历史消息失败: {e}")
        abort(500, description="加载历史消息失败")

    # 5. 构建完整上下文
    try:
        full_context = build_message_context(history_messages, user_message)
    except Exception as e:
        conn.close()
        print(f"构建消息上下文失败: {e}")
        abort(500, description="构建消息上下文失败")

    # 6. 准备助手消息存储
    assistant_message_id = str(uuid.uuid4())
    assistant_content = ""
    reasoning_content = ""
    reasoning_message_id = str(uuid.uuid4())

    def generate():
        nonlocal assistant_content, reasoning_content

        try:
            # 调用通信模块获取流式响应
            response_stream = communications.send_response_to_frontend(full_context, thinking)

            for chunk in response_stream:
                # 直接转发SSE格式的chunk
                yield chunk

                # 解析chunk，累积助手回复内容和思考内容
                if chunk.startswith('data: '):
                    try:
                        data_json = chunk[6:].strip()  # 去掉"data: "
                        if data_json:
                            data_obj = json.loads(data_json)
                            if not data_obj.get('done', True) and data_obj.get('success', True):
                                message_delta = data_obj.get('message_delta', '')
                                if data_obj.get('reasoning', False):
                                    # 累积思考内容
                                    reasoning_content += message_delta
                                else:
                                    # 累积助手回复内容
                                    assistant_content += message_delta
                    except json.JSONDecodeError:
                        continue

            # 流结束后保存消息
            if reasoning_content:
                # 保存思考内容
                save_reasoning_message(conversation_id, reasoning_message_id, reasoning_content)

            if assistant_content:
                # 保存助手回复
                save_assistant_message(conversation_id, assistant_message_id, assistant_content)

                # 只在对话首次有助手回复时生成标题
                # 检查是否已有非默认标题
                cur.execute("SELECT title FROM conversations WHERE id = ?", (conversation_id,))
                row = cur.fetchone()
                existing_title = row[0] if row else "新对话"

                if existing_title == "新对话":
                    # 生成并更新对话标题
                    title = generate_conversation_title(user_message, assistant_content)
                    if not update_conversation_title(conversation_id, title, force_update=True):
                        print(f"警告：对话 {conversation_id} 标题更新失败，保持为: {existing_title}")

            conn.close()

        except Exception as e:
            # 发生错误，回滚用户消息
            try:
                cur.execute("DELETE FROM messages WHERE id = ?", (user_message_id,))
                conn.commit()
            except:
                pass  # 忽略回滚错误
            finally:
                conn.close()

            # 发送错误消息
            error_msg = json.dumps({
                "success": False,
                "message": f"AI服务调用失败: {str(e)}",
                "done": True
            })
            yield f"data: {error_msg}\n\n"
            return

    return Response(generate(), mimetype='text/event-stream')

@app.route("/api/conversations", methods=['GET'])
def get_conversations():
    """获取所有对话列表，按创建时间倒序排列"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, title, created_at FROM conversations ORDER BY created_at DESC")

        conversations = []
        for row in cur.fetchall():
            conversations.append({
                "id": row[0],
                "title": row[1],
                "created_at": row[2]
            })

        conn.close()
        return jsonify({"success": True, "conversations": conversations})
    except Exception as e:
        print(f"获取对话列表失败: {e}")
        return jsonify({"success": False, "error": "获取对话列表失败"}), 500

@app.route("/api/chat/<conversation_id>/messages", methods=['GET'])
def get_conversation_messages(conversation_id):
    """获取特定对话的消息历史"""
    try:
        # 验证对话存在
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify({"success": False, "error": "对话不存在"}), 404

        # 获取消息（包含思考内容）
        cur.execute("""
            SELECT role, content, created_at, is_reasoning
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        """, (conversation_id,))

        messages = []
        for row in cur.fetchall():
            messages.append({
                "role": row[0],
                "content": row[1],
                "created_at": row[2],
                "is_reasoning": bool(row[3])  # 转换为布尔值
            })

        conn.close()
        return jsonify({"success": True, "messages": messages})
    except Exception as e:
        print(f"获取对话消息失败: {e}")
        return jsonify({"success": False, "error": "获取消息失败"}), 500

@app.route("/api/test",methods=['GET','POST'])
def test():
    response = {
        "uuid": '123456',
    }
    return jsonify(response)
    
# 确保数据库在应用启动时已初始化
ensure_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1",port=5000,debug=True) 
