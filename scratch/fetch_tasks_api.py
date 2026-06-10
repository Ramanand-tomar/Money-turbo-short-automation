import urllib.request
import json

def fetch():
    url = "http://127.0.0.1:8085/api/v1/tasks?page=1&page_size=50"
    req = urllib.request.Request(url)
    req.add_header("X-User-Id", "user_3EZD5UTvgVDMoAScLGKsxmX3x3h")
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            data = json.loads(res_body)
            print("API response status:", data.get("status"))
            tasks = data.get("data", {}).get("tasks", [])
            print("Total tasks returned:", len(tasks))
            for t in tasks:
                print(f"Task ID: {t.get('task_id')}, State: {t.get('state')}, Progress: {t.get('progress')}, Cloudinary: {t.get('cloudinary_url')}")
    except Exception as e:
        print("API request failed:", e)

if __name__ == "__main__":
    fetch()
