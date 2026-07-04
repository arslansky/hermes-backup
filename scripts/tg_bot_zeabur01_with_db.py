#!/usr/bin/env python3
"""
Zeabur01Bot - Standalone Telegram Bot with MiniMax API
Features: Direct conversation, chat history, SQLite logging
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.error
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ CONFIG ============
BOT_TOKEN = "875514…fx_s"
MINIMAX_API_KEY = "sk-cp-…gFVc"
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
DEFAULT_MODEL = "MiniMax-M2.7"
DB_FILE = "zeabur01_chat.db"

# ============ DATABASE ============
def init_db():
    """Initialize SQLite database for chat logging"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Chat messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            chat_id INTEGER,
            message_id INTEGER,
            role TEXT,
            content TEXT,
            model TEXT,
            timestamp TEXT,
            response_time_ms INTEGER
        )
    ''')
    
    # User sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            chat_id INTEGER,
            started_at TEXT,
            last_active TEXT,
            message_count INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def log_message(user_id, username, chat_id, message_id, role, content, model=None, response_time_ms=None):
    """Log a message to database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (user_id, username, chat_id, message_id, role, content, model, timestamp, response_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, chat_id, message_id, role, content, model, datetime.now().isoformat(), response_time_ms))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log message: {e}")

def update_session(user_id, username, first_name, last_name, chat_id):
    """Update or create user session"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if session exists
        cursor.execute('SELECT * FROM sessions WHERE user_id = ?', (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE sessions 
                SET last_active = ?, message_count = message_count + 1
                WHERE user_id = ?
            ''', (datetime.now().isoformat(), user_id))
        else:
            cursor.execute('''
                INSERT INTO sessions (user_id, username, first_name, last_name, chat_id, started_at, last_active, message_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', (user_id, username, first_name, last_name, chat_id, datetime.now().isoformat(), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to update session: {e}")

def get_chat_history(user_id, limit=20):
    """Get recent chat history for a user"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT role, content FROM messages 
            WHERE user_id = ? AND role IN ('user', 'assistant')
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        
        # Reverse to get chronological order
        history = []
        for role, content in reversed(rows):
            history.append({"role": role, "content": content})
        return history
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        return []

def get_stats():
    """Get bot statistics"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM messages')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM messages')
        total_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM messages WHERE role = "user"')
        user_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM messages WHERE role = "assistant"')
        bot_messages = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_users": total_users,
            "total_messages": total_messages,
            "user_messages": user_messages,
            "bot_messages": bot_messages
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {}

# ============ MINIMAX API ============
def ask_minimax(messages, model=DEFAULT_MODEL):
    """Send conversation to MiniMax API"""
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": MINIMAX_API_KEY
    }
    
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": 4096
    }, ensure_ascii=False).encode("utf-8")
    
    try:
        req = urllib.request.Request(
            f"{MINIMAX_BASE_URL}/v1/messages",
            data=payload,
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
            content = data.get("content", [])
            for item in content:
                if item.get("type") == "text":
                    text = item.get("text", "無回應")
                    return text.encode('utf-8', errors='replace').decode('utf-8')
            return "無回應"
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace') if hasattr(e, 'read') else str(e.reason)
        return f"API 錯誤: {e.code} - {error_body[:200]}"
    except Exception as e:
        return f"連線錯誤: {str(e)}"

# ============ HANDLERS ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any text message - direct conversation"""
    if not update.message or not update.message.text:
        return
    
    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    text = update.message.text
    
    logger.info(f"User {user_id} ({username}): {text[:50]}...")
    
    # Update session
    update_session(user_id, username, first_name, last_name, chat_id)
    
    # Log user message
    log_message(user_id, username, chat_id, message_id, "user", text)
    
    # Get chat history from database
    history = get_chat_history(user_id, limit=20)
    
    # Build messages with system prompt
    system_prompt = "你係一個有用嘅助手，用廣東話回答。"
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": text})
    
    # Show typing
    try:
        await update.message.chat.send_action(action="typing")
    except Exception as e:
        logger.warning(f"Typing indicator failed: {e}")
    
    # Get AI response
    start_time = datetime.now()
    response = ask_minimax(messages, DEFAULT_MODEL)
    response_time = int((datetime.now() - start_time).total_seconds() * 1000)
    
    logger.info(f"Response: {response[:50]}... ({response_time}ms)")
    
    # Log assistant response
    log_message(user_id, username, chat_id, message_id, "assistant", response, DEFAULT_MODEL, response_time)
    
    # Send response
    try:
        if len(response) > 4096:
            chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Send failed: {e}")
        safe_text = response.encode('utf-8', errors='replace').decode('utf-8', errors='replace')[:4000]
        await update.message.reply_text(safe_text)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset conversation history"""
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    chat_id = update.effective_chat.id
    
    # Log the reset action
    log_message(user_id, username, chat_id, None, "system", "User reset conversation")
    
    await update.message.reply_text("🗑️ 對話歷史已清除！")

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent chat history"""
    user_id = update.effective_user.id
    history = get_chat_history(user_id, limit=10)
    
    if not history:
        await update.message.reply_text("📭 暫無對話記錄")
        return
    
    text = "📜 最近對話:\n\n"
    for msg in history[-10:]:
        role = "👤" if msg["role"] == "user" else "🤖"
        content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
        text += f"{role} {content}\n\n"
    
    await update.message.reply_text(text)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    stats = get_stats()
    
    if not stats:
        await update.message.reply_text("❌ 無法獲取統計數據")
        return
    
    text = (
        "📊 Bot 統計:\n\n"
        f"👥 總用戶: {stats.get('total_users', 0)}\n"
        f"💬 總消息: {stats.get('total_messages', 0)}\n"
        f"👤 用戶消息: {stats.get('user_messages', 0)}\n"
        f"🤖 Bot回覆: {stats.get('bot_messages', 0)}\n"
    )
    
    await update.message.reply_text(text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot status"""
    user_id = update.effective_user.id
    history = get_chat_history(user_id, limit=1)
    
    await update.message.reply_text(
        f"✅ 在線\n"
        f"🤖 模型: {DEFAULT_MODEL}\n"
        f"💬 記錄: {'有' if history else '無'}\n"
        f"📡 API: MiniMax"
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    await update.message.reply_text(
        "👋 你好！我係 Zeabur01Bot\n"
        "直接發消息就可以同我對話\n"
        "所有對話會自動記錄\n\n"
        "可用命令:\n"
        "/reset - 清除對話歷史\n"
        "/history - 查看最近對話\n"
        "/stats - Bot統計數據\n"
        "/status - 查看狀態"
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

# ============ MAIN ============
def main():
    logger.info("Starting Zeabur01Bot...")
    logger.info(f"MiniMax API: {MINIMAX_BASE_URL}")
    logger.info(f"Default model: {DEFAULT_MODEL}")
    logger.info(f"Database: {DB_FILE}")
    
    # Initialize database
    init_db()
    
    # Build app
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    logger.info("Bot ready! Starting polling...")
    
    # Run
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        poll_interval=1.0,
        timeout=30
    )

if __name__ == "__main__":
    main()
