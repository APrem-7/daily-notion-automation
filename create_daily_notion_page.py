import os
import requests
from datetime import datetime

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID")
if not NOTION_TOKEN or not PARENT_PAGE_ID:
    raise SystemExit("Set NOTION_TOKEN and NOTION_PARENT_PAGE_ID in environment")

URL = "https://api.notion.com/v1/pages"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

TASKS = [
    "Morning review 🌞",
    "Top coding task 💻",
    "Read / Study 📖",
    "Workout 🏋️",
    "Plan next day 🧭"
]

def build_children(tasks):
    return [
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": task}}],
                "checked": False
            }
        } for task in tasks
    ]

def create_page():
    today = datetime.now().strftime("%Y-%m-%d")
    title = f"Daily ✅ {today}"
    payload = {
        "parent": {"type": "page_id", "page_id": PARENT_PAGE_ID},
        "properties": {"title": [{"type": "text", "text": {"content": title}}]},
        "children": build_children(TASKS)
    }
    response = requests.post(URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        print("✅ Created page:", title)
    else:
        print("❌ Failed:", response.status_code, response.text)
        response.raise_for_status()

if __name__ == "__main__":
    create_page()
