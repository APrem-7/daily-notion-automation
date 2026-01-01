import os
import requests
from datetime import datetime, timezone, timedelta
import time

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID")
if not NOTION_TOKEN or not PARENT_PAGE_ID:
    raise SystemExit("Set NOTION_TOKEN and NOTION_PARENT_PAGE_ID in environment")

PAGES_URL = "https://api.notion.com/v1/pages"
BLOCKS_URL = "https://api.notion.com/v1/blocks"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

TASKS = [
    "Leetcode 🧑🏻‍💻",
    "Top coding task 💻",
    "Workout 🏋️",
    "Plan next day 🧭",
    "Book Reading 📖",
    "Sandhyavandhan 🕉️",
    "Meditation 🕉️"
]

# Rate limiting delay between API calls (in seconds)
RATE_LIMIT_DELAY = 0.3


def ordinal(n: int) -> str:
    """Return ordinal string for an integer: 1 -> '1st', 2 -> '2nd', 3 -> '3rd', 4 -> '4th', ..."""
    # 11,12,13 are special -> 'th'
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


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


def get_all_child_pages(parent_id):
    """Get all child page blocks of a parent."""
    url = f"{BLOCKS_URL}/{parent_id}/children"
    all_pages = []
    has_more = True
    start_cursor = None
    
    while has_more:
        params = {"page_size": 100}
        if start_cursor:
            params["start_cursor"] = start_cursor
            
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            # Filter only child_page blocks
            all_pages.extend([r for r in results if r.get("type") == "child_page"])
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
        else:
            print(f"⚠️ Failed to get child pages: {response.status_code} - {response.text}")
            break
    
    return all_pages


def move_page_to_top(page_id, parent_id):
    """
    Move a page to the top by archiving all sibling pages and restoring in correct order.
    This is a workaround for Notion API's lack of direct reordering support.
    """
    # Get all child pages
    child_pages = get_all_child_pages(parent_id)
    
    if len(child_pages) <= 1:
        print("✅ Page is the only child or already at top")
        return True
    
    # Find the index of our new page
    new_page_index = None
    for i, page in enumerate(child_pages):
        if page["id"] == page_id:
            new_page_index = i
            break
    
    if new_page_index is None:
        print("⚠️ Could not find the new page in parent's children")
        return False
    
    if new_page_index == 0:
        print("✅ Page is already at the top")
        return True
    
    print(f"📋 Found {len(child_pages)} child pages, new page is at position {new_page_index + 1}")
    print("🔄 Reordering pages to move new page to top...")
    
    # Archive all pages except the new one
    pages_to_reorder = []
    for i, page in enumerate(child_pages):
        if page["id"] != page_id:
            # Archive this page
            archive_url = f"{PAGES_URL}/{page['id']}"
            archive_response = requests.patch(
                archive_url,
                headers=HEADERS,
                json={"archived": True}
            )
            if archive_response.status_code == 200:
                pages_to_reorder.append(page["id"])
                print(f"  📦 Archived page {i + 1}")
            else:
                print(f"  ⚠️ Failed to archive page {i + 1}")
            time.sleep(RATE_LIMIT_DELAY)
    
    # Archive the new page too
    archive_response = requests.patch(
        f"{PAGES_URL}/{page_id}",
        headers=HEADERS,
        json={"archived": True}
    )
    if archive_response.status_code != 200:
        print("⚠️ Failed to archive new page")
        return False
    print("  📦 Archived new page")
    time.sleep(RATE_LIMIT_DELAY)
    
    # Unarchive the new page first (it will be added at the end, which is now position 0)
    unarchive_response = requests.patch(
        f"{PAGES_URL}/{page_id}",
        headers=HEADERS,
        json={"archived": False}
    )
    if unarchive_response.status_code == 200:
        print("  📤 Restored new page (now at top)")
    else:
        print("  ⚠️ Failed to restore new page")
        return False
    time.sleep(RATE_LIMIT_DELAY)
    
    # Unarchive the rest in their original order
    for i, page_id_to_restore in enumerate(pages_to_reorder):
        unarchive_response = requests.patch(
            f"{PAGES_URL}/{page_id_to_restore}",
            headers=HEADERS,
            json={"archived": False}
        )
        if unarchive_response.status_code == 200:
            print(f"  📤 Restored page {i + 2}")
        else:
            print(f"  ⚠️ Failed to restore page {i + 2}")
        time.sleep(RATE_LIMIT_DELAY)
    
    print("✅ Successfully moved new page to the top!")
    return True


def create_page():
    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST)
    formatted_date = f"{now.strftime('%B')} {ordinal(now.day)}, {now.year}"
    title = f" {formatted_date}✅ "
    
    # Step 1: Create the page
    payload = {
        "parent": {"type": "page_id", "page_id": PARENT_PAGE_ID},
        "properties": {"title": [{"type": "text", "text": {"content": title}}]},
        "children": build_children(TASKS),
    }
    
    response = requests.post(PAGES_URL, headers=HEADERS, json=payload)
    if response.status_code != 200:
        print("❌ Failed to create page:", response.status_code, response.text)
        response.raise_for_status()
        return
    
    new_page_id = response.json()["id"]
    print(f"✅ Created page: {title}")
    
    # Step 2: Move the page to the top
    success = move_page_to_top(new_page_id, PARENT_PAGE_ID)
    if not success:
        print("⚠️ Warning: Failed to move page to top, it will remain at the bottom")


if __name__ == "__main__":
    create_page()
