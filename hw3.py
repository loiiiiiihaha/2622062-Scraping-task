import csv
import time
from collections import deque
from urllib.parse import urljoin, urlsplit, urldefrag

import requests
from bs4 import BeautifulSoup


START_URL = "https://www.musashino-u.ac.jp/"
DOMAIN = urlsplit(START_URL).netloc

# URLをキー、タイトルを値として保存する辞書
pages = {}

# これからアクセスするURL
queue = deque([START_URL])

# 登録済みのURL（重複を防ぐ）
seen = {START_URL}

# HTMLページではないファイルを除外する
SKIP_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg",
    ".webp", ".ico", ".css", ".js", ".zip",
    ".mp4", ".mp3", ".xlsx", ".docx", ".pptx",
)


def normalize_url(base_url, href):
    """相対URLを絶対URLに変換し、同じドメインか確認する。"""
    url = urljoin(base_url, href)
    url, _ = urldefrag(url)
    parts = urlsplit(url)

    if parts.scheme not in ("http", "https"):
        return None

    if parts.netloc != DOMAIN:
        return None

    if parts.path.lower().endswith(SKIP_EXTENSIONS):
        return None

    return url


def save_csv():
    """辞書の内容をCSVファイルに保存する。"""
    with open(
        "sitemap.csv", "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(["URL", "title"])
        writer.writerows(pages.items())


session = requests.Session()
session.headers["User-Agent"] = "UniversitySitemapStudy/1.0"

try:
    while queue:
        url = queue.popleft()
        print("アクセス中:", url)

        try:
            # アクセス前に2秒待ち、サーバーの負担を軽減する
            time.sleep(2)

            # リダイレクトも手動で処理し、毎回待機する
            response = session.get(
                url, timeout=30, allow_redirects=False
            )

            if response.is_redirect:
                next_url = normalize_url(
                    url, response.headers.get("Location", "")
                )
                if next_url and next_url not in seen:
                    seen.add(next_url)
                    queue.append(next_url)
                continue

            response.raise_for_status()

            # HTML以外は解析しない
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.lower():
                continue

            soup = BeautifulSoup(response.content, "html.parser")

            # ページのタイトルを辞書に保存
            title = (
                soup.title.get_text(strip=True)
                if soup.title else ""
            )
            pages[url] = title

            # ページ内のリンクを取得
            base_tag = soup.find("base", href=True)
            base_url = (
                urljoin(url, base_tag["href"]) if base_tag else url
            )

            for link in soup.find_all("a", href=True):
                next_url = normalize_url(base_url, link["href"])

                if next_url and next_url not in seen:
                    seen.add(next_url)
                    queue.append(next_url)

            # 途中でも結果が残るように保存
            save_csv()
            print(f"取得済み: {len(pages)} ページ")

        except requests.RequestException as error:
            print("取得失敗:", url, error)

except KeyboardInterrupt:
    print("\n処理を中断しました。")

finally:
    save_csv()
    session.close()
    print(f"sitemap.csv に {len(pages)} ページ保存しました。")