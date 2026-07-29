

# memory.py

import json
import os
import re
from django.conf import settings
from langchain_core.messages import HumanMessage, AIMessage

MEMORY_DIR = os.path.join(settings.BASE_DIR, "chat_memory")


# ----------------------------
# 📁 PATH HELPERS
# ----------------------------
def ensure_user_dir(user_id):
    user_dir = os.path.join(MEMORY_DIR, f"user_{user_id}")
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def get_memory_file(user_id, session_id):
    return os.path.join(ensure_user_dir(user_id), f"{session_id}.json")


def get_meta_file(user_id, session_id):
    return os.path.join(ensure_user_dir(user_id), f"{session_id}_meta.json")


def get_summary_file(user_id, session_id):
    return os.path.join(ensure_user_dir(user_id), f"{session_id}_summary.txt")


def get_long_term_file(user_id):
    return os.path.join(ensure_user_dir(user_id), "profile.json")


# ----------------------------
# 🧠 META
# ----------------------------
def load_meta(user_id, session_id):
    path = get_meta_file(user_id, session_id)

    if not os.path.exists(path):
        return {
            "total_messages": 0,
            "last_summary_update": 0
        }

    with open(path, "r") as f:
        return json.load(f)


def save_meta(user_id, session_id, meta):
    with open(get_meta_file(user_id, session_id), "w") as f:
        json.dump(meta, f, indent=2)


# ----------------------------
# 💬 SHORT TERM MEMORY
# ----------------------------
def load_messages(user_id, session_id):
    path = get_memory_file(user_id, session_id)

    if not os.path.exists(path):
        return []

    with open(path, "r") as f:
        data = json.load(f)

    messages = []
    for msg in data:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    return messages[-6:]  # 🔥 good balance


def normalize_content(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return " ".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )

    return str(content)


def append_message(user_id, session_id, role, content):
    path = get_memory_file(user_id, session_id)

    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
    else:
        data = []

    data.append({
        "role": role,
        "content": normalize_content(content)
    })

    data = data[-20:]  # 🔥 prevent growth

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    # update meta
    meta = load_meta(user_id, session_id)
    meta["total_messages"] += 1
    save_meta(user_id, session_id, meta)


# ----------------------------
# 📄 SUMMARY
# ----------------------------
def load_summary(user_id, session_id):
    path = get_summary_file(user_id, session_id)

    if not os.path.exists(path):
        return ""

    with open(path, "r") as f:
        return f.read()


def save_summary(user_id, session_id, summary):
    with open(get_summary_file(user_id, session_id), "w") as f:
        f.write(summary[:600])


def update_summary(llm, user_id, session_id, messages):
    meta = load_meta(user_id, session_id)

    if meta["total_messages"] - meta["last_summary_update"] < 5:
        return

    old = load_summary(user_id, session_id)

    prompt = f"""
Update conversation summary.

Old:
{old}

New:
{messages[-6:]}

Rules:
- Max 100 words
- Keep useful context
- Remove repetition
"""

    new_summary = llm.invoke(prompt).content

    save_summary(user_id, session_id, new_summary)

    meta["last_summary_update"] = meta["total_messages"]
    save_meta(user_id, session_id, meta)


# ----------------------------
# 👤 PROFILE MEMORY
# ----------------------------
def load_user_profile(user_id):
    path = get_long_term_file(user_id)

    if not os.path.exists(path):
        return {}

    with open(path, "r") as f:
        return json.load(f)


def save_user_profile(user_id, profile):
    with open(get_long_term_file(user_id), "w") as f:
        json.dump(profile, f, indent=2)


def is_profile_query(text):
    text = text.lower()
    return any(k in text for k in [
        "my name is",
        "call me",
        "i am",
        "i like",
        "i prefer"
    ])


def update_user_profile(llm, user_id, messages):
    existing = load_user_profile(user_id)

    prompt = f"""
Extract user info.

Return JSON only.

Schema:
{{
 "name": "",
 "preferences": [],
 "traits": []
}}

Existing:
{existing}

Conversation:
{messages[-6:]}
"""

    try:
        response = llm.invoke(prompt).content

        match = re.search(r"\{.*\}", response, re.DOTALL)
        data = json.loads(match.group(0)) if match else {}

        for k, v in data.items():
            if v:
                existing[k] = v

        save_user_profile(user_id, existing)

    except Exception as e:
        print("Profile error:", e)