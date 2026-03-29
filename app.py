from flask import Flask, abort, request, Response, stream_with_context, jsonify
from flask_cors import CORS
import sqlite3
from api import DeepSeekAPI
from datetime import datetime, timedelta
import uuid
import os
import communications

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
    data = request.get_json()
    if not data:
        abort(400)
    return Response()

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
