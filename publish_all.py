import os
import sys
import requests
from dotenv import load_dotenv


def read_markdown(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    message = ""
    for line in lines:
        if line.strip().startswith("#"):
            message += f"*{line.strip().lstrip('#').strip()}*\n"
        elif line.strip().startswith("- "):
            message += f"• {line.strip()[2:]}\n"
        else:
            message += line
    return message.strip()


def send_telegram_message(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found in .env")
        return
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
    )
    if response.status_code == 200:
        print("✅ Telegram: Message sent.")
    else:
        print(f"❌ Telegram: Failed - {response.text}")


if __name__ == "__main__":
    load_dotenv()
    if len(sys.argv) < 3 or "--post" not in sys.argv or "--to" not in sys.argv:
        print("Usage: python publish_all.py --post posts/blog_X.md --to telegram")
        sys.exit(1)

    post_file = sys.argv[sys.argv.index("--post") + 1]
    targets = sys.argv[sys.argv.index("--to") + 1].split(",")

    message = read_markdown(post_file)

    if "telegram" in targets:
        send_telegram_message(message)
