import os
import requests
from datetime import datetime,timezone,timedelta

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID")
if not NOTION_TOKEN or not PARENT_PAGE_ID:
    raise SystemExit("Set NOTION_TOKEN and NOTION_PARENT_PAGE_ID in environment")

URL = "https://api.notion.com/v1/pages"
SEARCH_URL = "https://api.notion.com/v1/search"
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

def get_or_create_monthly_page(year: int, month_name: str) -> str:
    """
    Get or create a monthly parent page (e.g., "December 2025").
    Returns the page ID of the monthly page.
    """
    monthly_title = f"{month_name} {year}"
    
    # Search for existing monthly page
    search_payload = {
        "query": monthly_title,
        "filter": {
            "value": "page",
            "property": "object"
        }
    }
    
    search_response = requests.post(SEARCH_URL, headers=HEADERS, json=search_payload)
    
    # Only process search results if the request was successful
    if search_response.status_code == 200:
        results = search_response.json().get("results", [])
        # Check if any result matches exactly and is a child of PARENT_PAGE_ID
        for result in results:
            if result.get("object") == "page":
                title_array = result.get("properties", {}).get("title", {}).get("title", [])
                if title_array and len(title_array) > 0:
                    page_title = title_array[0].get("text", {}).get("content", "")
                    if page_title == monthly_title:
                        # Verify it's a child of our parent page
                        parent = result.get("parent", {})
                        if parent.get("type") == "page_id" and parent.get("page_id") == PARENT_PAGE_ID:
                            print(f"📅 Found existing monthly page: {monthly_title}")
                            return result["id"]
    else:
        print(f"⚠️ Search request failed with status {search_response.status_code}, creating new monthly page")
    
    # Create new monthly page if not found or search failed
    print(f"📅 Creating new monthly page: {monthly_title}")
    monthly_payload = {
        "parent": {"type": "page_id", "page_id": PARENT_PAGE_ID},
        "properties": {"title": [{"type": "text", "text": {"content": monthly_title}}]},
        "children": []
    }
    
    create_response = requests.post(URL, headers=HEADERS, json=monthly_payload)
    
    if create_response.status_code == 200:
        monthly_page_id = create_response.json()["id"]
        print(f"✅ Created monthly page: {monthly_title}")
        return monthly_page_id
    else:
        error_msg = f"❌ Failed to create monthly page: {create_response.status_code}, {create_response.text}"
        print(error_msg)
        raise Exception(error_msg)

def create_page():

    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST)
    #today = datetime.now().strftime("%Y-%m-%d") 
    formatted_date = f"{now.strftime('%B')} {ordinal(now.day)}, {now.year}"
    title = f" {formatted_date}✅ "
    
    # Get or create the monthly parent page
    month_name = now.strftime('%B')
    year = now.year
    monthly_page_id = get_or_create_monthly_page(year, month_name)
    
    payload = {
        "parent": {"type": "page_id", "page_id": monthly_page_id},
        "properties": {"title": [{"type": "text", "text": {"content": title}}]},
        "children": build_children(TASKS),
        
    }
    response = requests.post(URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        print("✅ Created page:", title)
    else:
        print("❌ Failed:", response.status_code, response.text)
        response.raise_for_status()

if __name__ == "__main__":
    create_page()
