import os
import json
import yt_dlp
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import numpy as np


def get_twitch_highlight_links(channel_name, min_duration=None):
    """
    使用 yt-dlp API 獲取 Twitch 頻道內的所有精華片段 (Highlights)，可選擇過濾影片時長。

    :param channel_name: Twitch 頻道名稱，例如 "streamer_name"
    :param min_duration: 最小影片長度（分鐘），如果為 None 則不過濾
    :return: 包含所有符合條件的 Highlight 影片資訊的列表
    """
    twitch_channel_url = f"https://www.twitch.tv/{channel_name}/videos?filter=highlights&sort=time"

    ydl_opts = {
        "quiet": True,  # 不顯示過多日誌
        "extract_flat": True,  # 只獲取影片資訊，不下載
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(twitch_channel_url, download=False)
            if "entries" not in info:
                print("⚠️ 未找到任何精華片段。")
                return []

            highlight_urls = [
                video["url"] for video in info["entries"]
                if video and "duration" in video and (min_duration is None or video["duration"] >= min_duration * 60)
            ]

            return highlight_urls
        except yt_dlp.utils.DownloadError as e:
            print(f"❌ 獲取 Highlight 失敗: {e}")
            return []


def download_twitch_highlights(vod_url, output_path):
    options = {
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
        'format': 'best'
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([vod_url])


def authenticate_youtube():
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None

    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secrets.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(video_path, title, description, category_id="22", privacy_status="private"):
    youtube = authenticate_youtube()
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": privacy_status
            }
        },
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )
    response = request.execute()
    print(f"Upload Successful: {response}")


if __name__ == "__main__":
    channel_name = input("請輸入 Twitch 頻道名稱（例如 streamer_name）: ").strip()
    privacy = input("請選 YouTube 影片公開狀態（private/public）: ").strip()
    min_duration = int(input("請輸入最短影片時長（分）: "))
    authenticate_youtube()
    highlight_links = np.array(
        get_twitch_highlight_links(channel_name, min_duration))
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)
    if os.path.exists("local_highlights_links.txt") and os.path.getsize("local_highlights_links.txt") > 0:
        local_highlights_links = np.loadtxt(
            "local_highlights_links.txt", dtype=str)
    else:
        np.savetxt("local_highlights_links.txt",
                   highlight_links, delimiter="\n", fmt="%s")
        local_highlights_links = highlight_links
    tmp_highlights_links = local_highlights_links
    for local_highlight_link in local_highlights_links:
        vod_url = local_highlight_link.strip()
        print("Downloading VOD:", vod_url)
        download_twitch_highlights(vod_url, output_dir)
        video_name = [f for f in os.listdir(
            output_dir) if f.endswith(".mp4")][0]
        downloaded_video = os.path.join(output_dir, video_name)
        print(video_name.replace(".mp4", ""))
        print("Uploading to YouTube...")
        upload_to_youtube(downloaded_video, video_name,
                          "Uploaded from Twitch VOD", privacy_status=privacy)
        print("Uploading to YouTube successful!")
        print("Deleting local file...")
        os.remove(downloaded_video)
        print("Local file deleted!")
        print("Updating local highlights links...")
        tmp_highlights_links = np.delete(tmp_highlights_links, np.where(
            tmp_highlights_links == vod_url)[0])
        np.savetxt("local_highlights_links.txt", tmp_highlights_links,
                   delimiter="\n", fmt="%s")
        print("Local highlights links updated!")
