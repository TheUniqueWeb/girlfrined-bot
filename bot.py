import requests
import sqlite3
import time
import random
from datetime import datetime
from gtts import gTTS
import os

# ========= CONFIG =========
BOT_TOKEN = "7962954976:AAHstRkzjzGGKMe7fHNPCiSmyL75Z5KqPWY"
OPENAI_API_KEY = "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"

TG = f"https://api.telegram.org/bot{BOT_TOKEN}"
OPENAI = "https://api.openai.com/v1/chat/completions"

# ========= DB =========
conn = sqlite3.connect("memory.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS memory (
    chat_id TEXT,
    role TEXT,
    content TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    chat_id TEXT PRIMARY KEY,
    love INT,
    mood TEXT,
    nsfw INT
)
""")

# ========= TELEGRAM =========
def send(chat_id, text):
    requests.post(f"{TG}/sendMessage", data={"chat_id": chat_id, "text": text})

def typing(chat_id):
    requests.post(f"{TG}/sendChatAction", data={
        "chat_id": chat_id,
        "action": "typing"
    })

def send_voice(chat_id, text):
    tts = gTTS(text=text)
    file = "voice.mp3"
    tts.save(file)

    with open(file, "rb") as f:
        requests.post(f"{TG}/sendVoice", data={"chat_id": chat_id}, files={"voice": f})

    os.remove(file)

def send_avatar(chat_id):
    avatars = [
        "https://thispersondoesnotexist.com/image",
        "https://i.pravatar.cc/300"
    ]
    requests.post(f"{TG}/sendPhoto", data={
        "chat_id": chat_id,
        "photo": random.choice(avatars),
        "caption": "আজকের জন্য একটা ছবি... 😘"
    })

def updates(offset=None):
    return requests.get(f"{TG}/getUpdates", params={"offset": offset, "timeout": 100}).json()

# ========= MEMORY =========
def save_memory(chat_id, role, content):
    cur.execute("INSERT INTO memory VALUES (?, ?, ?)", (chat_id, role, content))
    conn.commit()

def get_memory(chat_id):
    cur.execute("SELECT role, content FROM memory WHERE chat_id=? ORDER BY rowid DESC LIMIT 20", (chat_id,))
    return cur.fetchall()[::-1]

# ========= USER =========
def get_user(chat_id):
    cur.execute("SELECT love, mood, nsfw FROM users WHERE chat_id=?", (chat_id,))
    u = cur.fetchone()

    if not u:
        cur.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (chat_id, 0, "normal", 0))
        conn.commit()
        return (0, "normal", 0)

    return u

def update_user(chat_id, love, mood, nsfw):
    cur.execute("UPDATE users SET love=?, mood=?, nsfw=? WHERE chat_id=?",
                (love, mood, nsfw, chat_id))
    conn.commit()

# ========= AI =========
def ai(chat_id, user_text, mood, nsfw):
    history = get_memory(chat_id)

    messages = []

    # system personality
    system_prompt = f"""
You are a romantic, emotional girlfriend.
Never say you are AI.
Mood: {mood}
NSFW level: {nsfw}
Be natural, human-like, flirty, caring.
"""

    messages.append({"role": "system", "content": system_prompt})

    for role, content in history:
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_text})

    res = requests.post(OPENAI, headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }, json={
        "model": "gpt-4o-mini",
        "messages": messages
    })

    reply = res.json()["choices"][0]["message"]["content"]

    save_memory(chat_id, "user", user_text)
    save_memory(chat_id, "assistant", reply)

    return reply

# ========= MOOD =========
def mood_detect(text):
    t = text.lower()
    if "sad" in t: return "sad"
    if "love" in t: return "romantic"
    if "angry" in t: return "angry"
    return "normal"

# ========= MAIN =========
offset = None
print("💖 GOD LEVEL GF RUNNING")

while True:
    data = updates(offset)

    for u in data["result"]:
        offset = u["update_id"] + 1

        if "message" not in u:
            continue

        chat_id = u["message"]["chat"]["id"]
        text = u["message"].get("text", "")

        love, mood, nsfw = get_user(chat_id)

        # commands
        if text == "/nsfw_on":
            nsfw = 1
            update_user(chat_id, love, mood, nsfw)
            send(chat_id, "😏 এখন আমি একটু naughty হতে পারি...")
            continue

        if text == "/nsfw_off":
            nsfw = 0
            update_user(chat_id, love, mood, nsfw)
            send(chat_id, "ঠিক আছে... আমি sweet থাকবো 💖")
            continue

        # typing animation
        typing(chat_id)
        time.sleep(random.uniform(1, 2.5))

        # mood + love
        mood = mood_detect(text)
        love += 1

        # AI reply
        reply = ai(chat_id, text, mood, nsfw)

        update_user(chat_id, love, mood, nsfw)

        send(chat_id, reply)

        # random advanced features
        if random.random() < 0.2:
            send_voice(chat_id, reply)

        if random.random() < 0.15:
            send_avatar(chat_id)

    time.sleep(1)
