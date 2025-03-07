import os
import json
import yt_dlp
import sys
import pickle
import time
import numpy as np
import requests
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox, QProgressBar
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


def get_twitch_highlight_links(channel_name, min_duration=None):
    twitch_channel_url = f"https://www.twitch.tv/{channel_name}/videos?filter=highlights&sort=time"
    ydl_opts = {"quiet": True, "extract_flat": True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(twitch_channel_url, download=False)
            if "entries" not in info:
                return []
            return [video["url"] for video in info["entries"] if video and "duration" in video and (min_duration is None or video["duration"] >= min_duration * 60)]
        except yt_dlp.utils.DownloadError:
            return []


def download_twitch_highlights(vod_url, output_path, progress_bar):
    options = {'outtmpl': f'{output_path}/%(title)s.%(ext)s', 'format': 'best'}
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([vod_url])


def authenticate_youtube():
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    if getattr(sys, "frozen", False):
        jsonpath = sys._MEIPASS
    else:
        jsonpath = os.path.dirname(os.path.abspath(__file__))
    datapath = os.path.join(jsonpath, "client_secrets.json")

    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                datapath, SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(video_path, title, description, category_id="22", privacy_status="private", callback=None):
    youtube = authenticate_youtube()
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description, "categoryId": category_id},
            "status": {"privacyStatus": privacy_status}
        },
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )
    response = request.execute()
    if callback:
        callback(response)

    return response


class DownloadWorker(QtCore.QThread):
    download_finished = QtCore.pyqtSignal(str, str)
    progress_update = QtCore.pyqtSignal(int)  # 進度更新訊號

    def __init__(self, vod_url, output_path, progress_bar):
        super().__init__()
        self.vod_url = vod_url
        self.output_path = output_path
        self.progress_bar = progress_bar

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes', d.get('total_bytes_estimate', 0))
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                percent = int((downloaded / total) * 100)
                self.progress_update.emit(percent)  # 發送進度訊號
                print(f"下載進度：{percent}%")  # 用於偵錯

    def run(self):
        options = {
            'outtmpl': f'{self.output_path}/%(title)s.%(ext)s', 'format': 'best', 'progress_hooks': [self.progress_hook]}
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([self.vod_url])
        self.progress_update.emit(100)  # 下載完成時，進度條設為 100%
        video_files = [f for f in os.listdir(
            self.output_path) if f.endswith(".mp4")]
        if video_files:
            video_name = video_files[0]
            self.download_finished.emit(self.vod_url, video_name)


class UploadWorker(QtCore.QThread):
    upload_finished = QtCore.pyqtSignal(dict, str)
    progress_update = QtCore.pyqtSignal(int)

    def __init__(self, video_path, title, privacy_status, vod_url, parent):
        super().__init__()
        self.video_path = video_path
        self.title = title
        self.privacy_status = privacy_status
        self.vod_url = vod_url
        self.parent = parent

    def run(self):
        youtube = authenticate_youtube()  # 你的 YouTube API 驗證函數
        media = MediaFileUpload(
            self.video_path, chunksize=1024 * 1024, resumable=True)

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": self.title,
                    "description": "Uploaded from Twitch VOD",
                },
                "status": {"privacyStatus": self.privacy_status},
            },
            media_body=media,
        )
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                percent = int(status.progress() * 100)
                self.progress_update.emit(percent)

        self.progress_update.emit(100)  # 上傳完成時，進度條設為 100%
        self.upload_finished.emit(response, self.vod_url)


class LoadVideoWorker(QtCore.QThread):
    videos_loaded = QtCore.pyqtSignal(list)  # 自訂訊號，回傳影片資訊

    def __init__(self, channel_name, min_duration):
        super().__init__()
        self.channel_name = channel_name
        self.min_duration = min_duration

    def run(self):
        if os.path.exists("local_highlights_links.txt") and os.path.getsize("local_highlights_links.txt") > 0:
            highlight_links = np.loadtxt(
                "local_highlights_links.txt", dtype=str)
        else:
            highlight_links = np.array(get_twitch_highlight_links(
                self.channel_name, self.min_duration))
            np.savetxt("local_highlights_links.txt",
                       highlight_links, delimiter="\n", fmt="%s")
        videos = []

        if highlight_links.size > 0:
            with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
                for link in highlight_links:
                    try:
                        info = ydl.extract_info(link, download=False)
                        title = info.get("title", "Unknown Title")
                        thumbnail = info.get("thumbnail", "")
                        videos.append((title, link, thumbnail))
                    except Exception as e:
                        print(f"無法獲取影片資訊: {e}")

        self.videos_loaded.emit(videos)  # 傳回結果


class TwitchToYouTubeApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.upload_workers = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Twitch 精華下載 & 上傳 YouTube")
        layout = QtWidgets.QVBoxLayout()
        self.setMinimumSize(960, 720)

        self.channel_label = QtWidgets.QLabel("Twitch 頻道名稱:")
        self.channel_input = QtWidgets.QLineEdit()

        self.duration_label = QtWidgets.QLabel("最短影片時長 (分鐘):")
        self.duration_input = QtWidgets.QLineEdit()

        self.privacy_label = QtWidgets.QLabel("YouTube 影片公開狀態:")
        self.privacy_combo = QtWidgets.QComboBox()
        self.privacy_combo.addItems(["private", "public"])

        self.video_list_widget = QtWidgets.QListWidget()
        self.video_list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.MultiSelection)
        self.video_list_widget.setIconSize(QtCore.QSize(96, 54))

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.start_button = QtWidgets.QPushButton("開始處理")
        self.start_button.clicked.connect(self.start_process)

        self.load_button = QtWidgets.QPushButton("載入影片清單")
        self.load_button.clicked.connect(self.load_video_process)

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: red;")
        self.status_label.hide()

        layout.addWidget(self.channel_label)
        layout.addWidget(self.channel_input)
        layout.addWidget(self.duration_label)
        layout.addWidget(self.duration_input)
        layout.addWidget(self.privacy_label)
        layout.addWidget(self.privacy_combo)
        layout.addWidget(QtWidgets.QLabel("選擇要下載與上傳的影片:"))
        layout.addWidget(self.video_list_widget)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.load_button)
        layout.addWidget(self.start_button)

        # 將 status_label 添加到 UI 佈局
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def start_process(self):
        privacy = self.privacy_combo.currentText()
        self.output_dir = "downloads"
        os.makedirs(self.output_dir, exist_ok=True)

        selected_items = self.video_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "請選擇至少一個影片進行處理。")
            return
        self.highlight_links = [item.text() for item in selected_items]
        self.process_next_video()

    def load_video_process(self):
        self.video_list_widget.clear()
        channel_name = self.channel_input.text().strip()
        try:
            min_duration = int(self.duration_input.text())
        except ValueError:
            QMessageBox.critical(self, "錯誤", "請輸入有效的數字作為影片時長")
            return
        self.start_button.setVisible(False)  # 隱藏開始按鈕
        self.load_button.setVisible(False)  # 隱藏載入按鈕
        self.status_label.setText("正在載入影片...")
        self.status_label.show()
        self.load_video_worker = LoadVideoWorker(channel_name, min_duration)
        self.load_video_worker.videos_loaded.connect(self.on_videos_loaded)
        self.load_video_worker.start()

    def process_next_video(self):
        if not self.highlight_links:
            print("所有影片處理完成！")  # Debug
            QMessageBox.information(self, "完成", "所有選擇的影片已成功處理！")
            self.progress_bar.setValue(0)
            self.reset_ui()
            return
        self.start_button.setVisible(False)  # 隱藏按鈕
        self.load_button.setVisible(False)  # 隱藏按鈕
        self.status_label.setText("下載影片中...")
        self.status_label.show()

        vod_entry = self.highlight_links.pop(0)
        vod_url = vod_entry.split(" - ")[-1]  # 取出網址部分
        print(f"開始下載影片：{vod_url}")
        self.progress_bar.setValue(0)

        self.download_worker = DownloadWorker(
            vod_url, self.output_dir, self.progress_bar)
        self.download_worker.progress_update.connect(
            self.progress_bar.setValue)  # 連接進度更新
        self.download_worker.download_finished.connect(
            self.on_download_finished)
        self.download_worker.start()

    def on_videos_loaded(self, videos):
        self.reset_ui()
        if not videos:
            QMessageBox.warning(self, "提示", "未找到符合條件的影片。")
            return

        for title, link, thumbnail in videos:
            display_text = f"{title} - {link}"
            item = QtWidgets.QListWidgetItem(display_text)
            item.setSizeHint(QtCore.QSize(192, 108))  # 設定選項高度與預覽圖一致

            if thumbnail:
                image = QtGui.QImage()
                image.loadFromData(requests.get(thumbnail).content)
                pixmap = QtGui.QPixmap(image).scaled(
                    192, 108, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                icon = QtGui.QIcon(pixmap)
                item.setIcon(icon)

            self.video_list_widget.addItem(item)

    def on_download_finished(self, vod_url, video_name):
        video_path = os.path.join(self.output_dir, video_name)
        print(f"下載完成：{video_name}，開始上傳到 YouTube...")
        self.progress_bar.setValue(0)

        self.status_label.setText("上傳影片中...")

        self.upload_worker = UploadWorker(video_path, video_name.replace(
            ".mp4", ""), self.privacy_combo.currentText(), vod_url, self)
        self.upload_worker.progress_update.connect(
            self.progress_bar.setValue)  # 連接上傳進度
        self.upload_worker.upload_finished.connect(self.on_upload_finished)
        self.upload_worker.start()
        print("🚀 UploadWorker 已啟動")

    def on_upload_finished(self, response, vod_url):
        print(f"影片 {vod_url} 上傳完成，準備移除並下載下一個影片...")  # Debug
        self.progress_bar.setValue(100)

        if os.path.exists("local_highlights_links.txt"):
            local_highlights_links = np.loadtxt(
                "local_highlights_links.txt", dtype=str)
            updated_links = local_highlights_links[local_highlights_links != vod_url]
            np.savetxt("local_highlights_links.txt",
                       updated_links, delimiter="\n", fmt="%s")

        # 从 QListWidget 中移除该影片
        for i in range(self.video_list_widget.count()):
            item = self.video_list_widget.item(i)
            if item.text().split(" - ")[-1] == vod_url:
                self.video_list_widget.takeItem(i)
                break  # 移除后立即跳出，避免错误

        video_files = [f for f in os.listdir(
            self.output_dir) if f.endswith(".mp4")]
        if video_files:
            video_name = video_files[0]
            video_path = os.path.join(self.output_dir, video_name)

            time.sleep(1)  # 稍等1秒，避免文件佔用
            try:
                os.remove(video_path)  # 刪除影片
                print(f"影片 {video_name} 已刪除")  # Debug
            except PermissionError:
                print(f"無法刪除 {video_path}，請稍後手動刪除。")
        QtCore.QTimer.singleShot(500, self.process_next_video)

    def reset_ui(self):
        self.start_button.setVisible(True)
        self.load_button.setVisible(True)
        self.status_label.hide()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = TwitchToYouTubeApp()
    authenticate_youtube()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
