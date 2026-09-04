import json
import os
import random
import re
import tempfile
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tweetkit_x import TweetKit


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

COOKIE_FILE = os.path.join(BASE_DIR, "cookie.txt")
IMAGE_LIST_FILE = os.path.join(BASE_DIR, "images.txt")
STATE_FILE = os.path.join(BASE_DIR, "scheduled.json")

TIMEZONE = ZoneInfo("Asia/Taipei")

POST_TIMES = [
    (10, 29),
    (22, 29),
]

SCHEDULE_DAYS = 7


def load_images():
    with open(IMAGE_LIST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    images = []

    for item in data.get("origin", []):
        match = re.search(r"\{img\s+(https?://\S+?)\}", item)

        if match:
            images.append(match.group(1))

    if not images:
        raise RuntimeError("没有找到任何图片 URL")

    return images


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def download_image(url):
    temp = tempfile.NamedTemporaryFile(
        suffix=".png",
        delete=False
    )

    temp_path = temp.name
    temp.close()

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            with open(temp_path, "wb") as f:
                f.write(response.read())

        return temp_path

    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def main():
    print("===================================")
    print("       DCI SCREENSHOT SCHEDULER")
    print("===================================")

    images = load_images()
    state = load_state()

    print(f"图片数量：{len(images)}")

    tk = TweetKit(cookie_file=COOKIE_FILE)

    now = datetime.now(TIMEZONE)

    print(f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    scheduled_count = 0

    for day_offset in range(SCHEDULE_DAYS):
        date = (now + timedelta(days=day_offset)).date()

        for hour, minute in POST_TIMES:
            dt = datetime(
                date.year,
                date.month,
                date.day,
                hour,
                minute,
                tzinfo=TIMEZONE
            )

            if dt <= now:
                continue

            slot = dt.strftime("%Y-%m-%d %H:%M")

            if slot in state:
                print(f"跳过已安排：{slot}")
                continue

            image_url = random.choice(images)

            print(f"\n安排：{slot}")
            print(f"图片：{image_url}")

            image_path = None

            try:
                image_path = download_image(image_url)

                timestamp = int(dt.timestamp())

                result = tk.schedule(
                    "",
                    timestamp,
                    image_path
                )

                if not result.get("ok"):
                    raise RuntimeError(result)

                state[slot] = {
                    "scheduled_id": result["scheduled_id"],
                    "image_url": image_url,
                    "scheduled_at": slot,
                }

                save_state(state)

                print(f"成功：{result['scheduled_id']}")

                scheduled_count += 1

            except Exception as e:
                print(f"失败：{e}")

            finally:
                if image_path and os.path.exists(image_path):
                    os.remove(image_path)

    print("\n===================================")
    print(f"本次新安排：{scheduled_count} 条")
    print("===================================")


if __name__ == "__main__":
    main()