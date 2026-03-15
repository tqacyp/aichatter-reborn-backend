-- 开启外键约束支持（SQLite默认关闭，务必开启）
PRAGMA foreign_keys = ON;

-- 会话表
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,  -- 存储UUID，如 'abc-123...'
    title TEXT NOT NULL DEFAULT '新对话',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
);

-- 消息表
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')), -- 限制角色值
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE -- 会话删除时，关联消息自动删除
);

-- 创建索引以加速查询
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- （可选）如果多用户，为用户ID创建索引
-- CREATE INDEX idx_conversations_user_id ON conversations(user_id);