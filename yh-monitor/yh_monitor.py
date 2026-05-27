#!/usr/bin/env python3
"""
异环微博监控 — GitHub Actions 版
每5分钟自动检查 @异环 新微博 → Server酱 → 微信通知
"""

import os, json, re, sys
import requests

SENDKEY = os.environ.get("SCT_SENDKEY", "")
WEIBO_UID = "7929584207"
WEIBO_API = f"https://m.weibo.cn/api/container/getIndex?type=uid&value={WEIBO_UID}&containerid=107603{WEIBO_UID}"
STATE_FILE = "yh_state.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605.1.15"
}

def send_wechat(title, content):
    if not SENDKEY:
        return False
    try:
        r = requests.post(f"https://sctapi.ftqq.com/{SENDKEY}.send",
                          data={"title": title, "desp": content}, timeout=10)
        ok = r.json().get("code") == 0
        print(f"  {'OK' if ok else 'FAIL'} Push: {title}")
        return ok
    except Exception as e:
        print(f"  ERR Push: {e}")
        return False

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"weibo_last_id": ""}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False)

def check_weibo(state):
    try:
        data = requests.get(WEIBO_API, headers=HEADERS, timeout=15).json()
        if data.get("ok") != 1:
            return [], state
        cards = data["data"]["cards"]
        last_id = state.get("weibo_last_id", "")
        new_posts = []
        for card in cards:
            if card.get("card_type") != 9:
                continue
            mblog = card["mblog"]
            pid = mblog["id"]
            if pid <= last_id:
                break
            text = re.sub(r"<[^>]+>", "", mblog.get("text", "")).strip()[:300]
            new_posts.append({
                "id": pid,
                "time": mblog["created_at"],
                "text": text,
                "link": f"https://m.weibo.cn/detail/{pid}"
            })
        # 更新最新ID
        if cards and cards[0].get("card_type") == 9:
            top_id = cards[0]["mblog"]["id"]
            if top_id > last_id:
                state["weibo_last_id"] = top_id
        return new_posts, state
    except Exception as e:
        print(f"ERR: {e}")
        return [], state

if __name__ == "__main__":
    print(f"Check @异环 Weibo...")
    state = load_state()
    new_posts, state = check_weibo(state)
    if new_posts:
        print(f"  NEW: {len(new_posts)} posts")
        for post in reversed(new_posts):
            send_wechat("🔔 @异环 新微博",
                        f"📅 {post['time']}\n\n{post['text']}\n\n🔗 {post['link']}")
    else:
        print("  OK: No new posts")
    save_state(state)
    print("DONE")
