from flask import Flask, abort
import sqlite3
from api import DeepSeekAPI
from datetime import datetime, timedelta
import uuid
import os

"""
    app.py 功能: aichatter-reborn 后端，负责处理api请求，并实现与数据库交互
"""

app = Flask(__name__)
deepseek_api = DeepSeekAPI()
DB_PATH = os.path.join(os.path.dirname(__file__),"messages.db")
SQL_PATH = os.path.join(os.path.dirname(__file__),"schema.sql")

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

@app.route("/")
def index():
    abort(404)

@app.route("/api/send",methods=['POST'])
def send_request():
    
    abort(404)
    
if __name__ == "__main__":
    app.run(host="127.0.0.1",port=5000,debug=True) 
