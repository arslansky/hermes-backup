#!/usr/bin/env python3
"""
Zeabur01Bot - Standalone Telegram Bot with TTK + MiniMax
Features: Direct conversation, image analysis with TTK gemini, chat history
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.error
import base64
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
BOT_TOKEN = "8755148273:AAEM7NYxmS1SSrSKSQy5XZfIVFOjiDkfx_s"

# TTK API
TTK_API_KEY = os.environ.get('TTK_API_KEY', '***')
TTK_BASE_URL = "https://api.ttk.homes/v1"

# Default models
DEFAULT_TEXT_MODEL = "MiniMax-M2.7"  # 你要求用 MiniMax 做 default
DEFAULT_VISION_MODEL = "gemini-3.5-flash"  # TTK gemini for vision

DB_FILE = "zeabur01_chat.db"

# Store conversation history per user
user_chats = {}
MAX_HISTORY = 20

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

# ============ TTK API ============
def ask_ttk_text(messages, model=DEFAULT_TEXT_MODEL):
    """Send text conversation to TTK API"""
    headers = {
        "Authorization": f"Bearer {TTK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": 4096
    }, ensure_ascii=False).encode("utf-8")
    
    try:
        req = urllib.request.Request(
            f"{TTK_BASE_URL}/chat/completions",
            data=payload,
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "無回應")
            return content.encode('utf-8', errors='replace').decode('utf-8')
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace') if hasattr(e, 'read') else ""
        return f"API 錯誤: {e.code} - {error_body[:200]}"
    except Exception as e:
        return f"連線錯誤: {str(e)}"

def ask_ttk_vision(image_base64, prompt="分析呢張圖", model=DEFAULT_VISION_MODEL):
    """Send image to TTK gemini for analysis"""
    headers = {
        "Authorization": f"Bearer {TTK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = json.dumps({
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 4096
    }, ensure_ascii=False).encode("utf-8")
    
    try:
        req = urllib.request.Request(
            f"{TTK_BASE_URL}/chat/completions",
            data=payload,
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "無回應")
            return content.encode('utf-8', errors='replace').decode('utf-8')
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace') if hasattr(e, 'read') else ""
        return f"API 錯誤: {e.code} - {error_body[:200]}"
    except Exception as e:
        return f"連線錯誤: {str(e)}"

# ============ TELEGRAM HANDLERS ============
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages - use MiniMax (default)"""
    if not update.message or not update.message.text:
        return
    
    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    text = update.message.text
    
    logger.info(f"User {user_id} ({username}): {text[:50]}...")
    
    # Initialize chat history
    if user_id not in user_chats:
        user_chats[user_id] = {
            "history": [],
            "model": DEFAULT_TEXT_MODEL
        }
    
    # Add user message
    user_chats[user_id]["history"].append({
        "role": "user",
        "content": text
    })
    
    # Trim history
    if len(user_chats[user_id]["history"]) > MAX_HISTORY:
        user_chats[user_id]["history"] = user_chats[user_id]["history"][-MAX_HISTORY:]
    
    # Build messages
    system_prompt = "你係一個有用嘅助手，用廣東話回答。"
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(user_chats[user_id]["history"])
    
    # Show typing
    try:
        await update.message.chat.send_action(action="typing")
    except Exception as e:
        logger.warning(f"Typing indicator failed: {e}")
    
    # Get response from MiniMax (default)
    start_time = datetime.now()
    response = ask_ttk_text(messages, DEFAULT_TEXT_MODEL)
    response_time = int((datetime.now() - start_time).total_seconds() * 1000)
    
    logger.info(f"Response: {response[:50]}... ({response_time}ms)")
    
    # Add to history
    user_chats[user_id]["history"].append({
        "role": "assistant",
        "content": response
    })
    
    # Log
    log_message(user_id, username, chat_id, message_id, "user", text)
    log_message(user_id, username, chat_id, message_id, "assistant", response, DEFAULT_TEXT_MODEL, response_time)
    
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

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle images - use TTK gemini for analysis"""
    if not update.message or not update.message.photo:
        return
    
    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    
    logger.info(f"User {user_id} sent image, analyzing with TTK gemini...")
    
    # Show typing
    try:
        await update.message.chat.send_action(action="typing")
    except Exception as e:
        logger.warning(f"Typing indicator failed: {e}")
    
    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Download image
        image_bytes = await file.download_as_bytearray()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        logger.info(f"Image downloaded: {len(image_bytes)} bytes")
        
        # Analyze with TTK gemini
        start_time = datetime.now()
        response = ask_ttk_vision(
            image_base64,
            prompt="詳細分析呢張圖：1. 顏色搭配 2. 排版結構 3. 視覺衝擊力 4. 設計風格 5. 文化特徵。用廣東話回答。",
            model=DEFAULT_VISION_MODEL
        )
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        logger.info(f"Vision analysis: {response[:50]}... ({response_time}ms)")
        
        # Log
        log_message(user_id, username, chat_id, message_id, "user", "[IMAGE]")
        log_message(user_id, username, chat_id, message_id, "assistant", response, DEFAULT_VISION_MODEL, response_time)
        
        # Send response
        if len(response) > 4096:
            chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(response)
            
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        await update.message.reply_text(f"❌ 圖片分析失敗: {str(e)}")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset conversation"""
    user_id = update.effective_user.id
    if user_id in user_chats:
        user_chats[user_id]["history"] = []
    await update.message.reply_text("🗑️ 對話歷史已清除！")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show status"""
    user_id = update.effective_user.id
    chat_info = user_chats.get(user_id, {"history": [], "model": DEFAULT_TEXT_MODEL})
    await update.message.reply_text(
        f"✅ 在線\n"
        f"🤖 文字模型: {DEFAULT_TEXT_MODEL}\n"
        f"👁️ 圖片模型: {DEFAULT_VISION_MODEL}\n"
        f"💬 對話長度: {len(chat_info['history'])}"
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome"""
    await update.message.reply_text(
        "👋 你好！我係 Zeabur01Bot\n"
        "🤖 文字對話用 MiniMax\n"
        "👁️ 圖片分析用 TTK Gemini\n\n"
        "直接發消息或圖片就可以！\n\n"
        "/reset - 清除歷史\n"
        "/status - 查看狀態"
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

# ============ MAIN ============
def main():
    logger.info("Starting Zeabur01Bot with TTK + MiniMax...")
    logger.info(f"Text model: {DEFAULT_TEXT_MODEL}")
    logger.info(f"Vision model: {DEFAULT_VISION_MODEL}")
    
    # Initialize database
    init_db()
    
    # Build app
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("status", status_command))
    
    # Text messages -> MiniMax
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Images -> TTK Gemini
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    
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
