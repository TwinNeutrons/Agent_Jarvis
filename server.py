from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
import os
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

load_dotenv()

WAHA_API_KEY = os.getenv("WAHA_API_KEY")
WAHA_BASE_URL = os.getenv("WAHA_BASE_URL")
OLLAMA_URL = os.getenv("OLLAMA_URL")
SESSION_NAME = os.getenv("SESSION_NAME")


app = Flask(__name__)
memory_store = {}

def get_memory(chat_id):
    history = memory_store.get(chat_id, [])
    
    logger.debug(f"[MEMORY] Fetch | chat_id={chat_id} | size={len(history)}")
    
    return history

def update_memory(chat_id, role, content):
    if chat_id not in memory_store:
        memory_store[chat_id] = []
        logger.info(f"[MEMORY] New chat initialized | chat_id={chat_id}")

    memory_store[chat_id].append({
        "role": role,
        "content": content
    })

    # trim memory
    if len(memory_store[chat_id]) > 10:
        memory_store[chat_id] = memory_store[chat_id][-10:]
        logger.debug(f"[MEMORY] Trimmed | chat_id={chat_id}")

    logger.debug(
        f"[MEMORY] Update | chat_id={chat_id} | role={role} | size={len(memory_store[chat_id])}"
    )

def ask_ollama(prompt, chat_id):
    history = get_memory(chat_id)

    history_text = "\n".join([
        f"{m['role']}: {m['content']}" for m in history
    ])

    full_prompt = f"""
You are Jarvis, a smart and concise AI assistant.

Conversation history:
{history_text}

User: {prompt}
"""

    payload = {
        "model": "mistral",
        "prompt": full_prompt,
        "stream": False
    }

    logger.info(f"[OLLAMA] Request | chat_id={chat_id}")
    logger.debug(f"[OLLAMA] Prompt:\n{full_prompt}")

    try:
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)

        if response.status_code != 200:
            logger.error(f"[OLLAMA] Error {response.status_code}: {response.text}")
            return "Error talking to Ollama"

        result = response.json().get("response", "")

        logger.info(f"[OLLAMA] Response received | chat_id={chat_id}")
        logger.debug(f"[OLLAMA] Response: {result}")

        return result

    except Exception:
        logger.exception("[OLLAMA] Exception")
        return "Error talking to Ollama"
    
def send_message(chat_id, text, reply_to=None):
    url = f"{WAHA_BASE_URL}/api/sendText"
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": WAHA_API_KEY
    }

    payload = {
        "chatId": chat_id,
        "text": text,
        "session": SESSION_NAME
    }

    if reply_to:
        payload["replyTo"] = reply_to

    logger.info(f"Sending message to WAHA | chat_id={chat_id}")

    try:
        res = requests.post(url, json=payload, headers=headers)
        data = res.json()

        body = data.get("_data", {}).get("body")

        logger.info(f"WAHA response | status={res.status_code}")
        logger.debug(f"WAHA body: {body}")

    except Exception as e:
        logger.exception("Failed to send message via WAHA")

@app.route("/bot", methods=["POST"])
def bot():
    data = request.json

    logger.info("Incoming webhook received")

    if data.get("event") == "message.any":
        payload = data.get("payload", {})
        
        message = payload.get("body", "")
        from_me = payload.get("fromMe", False)
        message_id = payload.get("id")

        chat_id = payload.get("to") if from_me else payload.get("from")

        logger.info(f"Message received | chat_id={chat_id} | from_me={from_me}")
        logger.debug(f"Message: {message}")

        if message.lower().startswith("!jarvis"):
            
            user_prompt = message.replace("!jarvis", "").strip()
            logger.info(f"Command detected | prompt={user_prompt}")
            response = ask_ollama(user_prompt, chat_id)

            update_memory(chat_id, "user", user_prompt)
            update_memory(chat_id, "assistant", response)

            logger.debug(f"[MEMORY CONTENT] {memory_store[chat_id]}")
            
            send_message(chat_id, response, reply_to=message_id)

    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)