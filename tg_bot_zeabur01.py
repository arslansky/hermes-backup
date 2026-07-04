#!/usr/bin/env python3
"""
Zeabur01Bot - Standalone Telegram Bot with MiniMax API
Direct conversation, no commands needed
"""

import os
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

# ============ CONFIG ============
BOT_TOKEN = "8755148273:AAEM7NYxmS1SSrSKSQy5XZfIVFOjiDkfx_s"
MINIMAX_API_KEY = "sk-cp-mNrtisBo685K4E_h9tViioU44JVLDP89yIhrVXnSqJUOH8pCoK0DdMV2qN0JhIpqhH9RU84B5wd6JyW4t6JnOJYaJGMfagw1ogF1gsSwrQoEVla8-ufgFVc"
MINIMAX_BASE_URL = "https://api.minimax.io/anthropic"
DEFAULT_MODEL = "MiniMax-M2.7"

# Store conversation history per user
user_chats = {}
MAX_HISTORY = 20  # Keep last 20 messages

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
    }).encode("utf-8")
    
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
                    return item.get("text", "無回應")
            return "無回應"
    except urllib.error.HTTPError as e:
        return f"API 錯誤: {e.code} - {e.reason}"
    except Exception as e:
        return f"連線錯誤: {str(e)}"

# ============ TELEGRAM HANDLERS ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any text message - direct conversation"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "User"
    text = update.message.text
    
    # Initialize chat history if new user
    if user_id not in user_chats:
        user_chats[user_id] = {
            "history": [],
            "model": DEFAULT_MODEL
        }
    
    # Add user message to history
    user_chats[user_id]["history"].append({
        "role": "user",
        "content": text
    })
    
    # Keep only last N messages
    if len(user_chats[user_id]["history"]) > MAX_HISTORY:
        user_chats[user_id]["history"] = user_chats[user_id]["history"][-MAX_HISTORY:]
    
    # Build messages with system prompt
    system_prompt = "你係一個有用嘅助手，用廣東話回答。"
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(user_chats[user_id]["history"])
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Get AI response
    model = user_chats[user_id]["model"]
    response = ask_minimax(messages, model)
    
    # Add assistant response to history
    user_chats[user_id]["history"].append({
        "role": "assistant",
        "content": response
    })
    
    # Send response (truncate if too long for Telegram)
    if len(response) > 4096:
        # Split into chunks
        chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
        for chunk in chunks:
            await update.message.reply_text(chunk)
    else:
        await update.message.reply_text(response)

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset conversation history"""
    user_id = update.effective_user.id
    if user_id in user_chats:
        user_chats[user_id]["history"] = []
    await update.message.reply_text("🗑️ 對話歷史已清除。新對話開始！")

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show or switch model"""
    user_id = update.effective_user.id
    
    if user_id not in user_chats:
        user_chats[user_id] = {"history": [], "model": DEFAULT_MODEL}
    
    if context.args:
        new_model = context.args[0]
        user_chats[user_id]["model"] = new_model
        await update.message.reply_text(f"🔄 已切換至模型: {new_model}")
    else:
        current = user_chats[user_id]["model"]
        await update.message.reply_text(
            f"🤖 當前模型: {current}\n"
            f"可用模型: MiniMax-M2.7, MiniMax-M3\n"
            f"用法: /model MiniMax-M3"
        )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot status"""
    user_id = update.effective_user.id
    chat_info = user_chats.get(user_id, {"history": [], "model": DEFAULT_MODEL})
    
    await update.message.reply_text(
        f"✅ Bot 狀態: 在線\n"
        f"🤖 當前模型: {chat_info['model']}\n"
        f"💬 對話長度: {len(chat_info['history'])} 條消息\n"
        f"📡 API: MiniMax"
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    await update.message.reply_text(
        "👋 你好！我係 Zeabur01Bot\n"
        "直接發消息就可以同我對話\n"
        "\n可用命令:\n"
        "/reset - 清除對話歷史\n"
        "/model - 查看/切換模型\n"
        "/status - 查看狀態"
    )

# ============ MAIN ============
def main():
    print(f"[{datetime.now()}] Starting Zeabur01Bot...")
    print(f"[{datetime.now()}] MiniMax API: {MINIMAX_BASE_URL}")
    print(f"[{datetime.now()}] Default model: {DEFAULT_MODEL}")
    
    # Build application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(CommandHandler("status", status_command))
    
    # Handle all text messages (not commands)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print(f"[{datetime.now()}] Bot started! Waiting for messages...")
    
    # Run with auto-reconnect
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        poll_interval=1.0
    )

if __name__ == "__main__":
    main()
