import os
import requests
import subprocess
import zipfile
import sys
from pathlib import Path

# === 1️⃣ 自动下载 FFmpeg Windows 版本 ===
def download_ffmpeg():
    ffmpeg_dir = Path("ffmpeg")
    ffmpeg_exe = ffmpeg_dir / "ffmpeg.exe"
    if ffmpeg_exe.exists():
        print("✅ FFmpeg 已存在。")
        return
    print("⬇️ 正在下载 FFmpeg（约70MB）...")
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    r = requests.get(url, stream=True)
    with open("ffmpeg.zip", "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            f.write(chunk)
    print("✅ 下载完成，正在解压...")
    with zipfile.ZipFile("ffmpeg.zip", "r") as zip_ref:
        zip_ref.extractall("ffmpeg_tmp")
    for root, dirs, files in os.walk("ffmpeg_tmp"):
        for file in files:
            if file == "ffmpeg.exe":
                ffmpeg_dir.mkdir(exist_ok=True)
                os.rename(os.path.join(root, file), ffmpeg_exe)
                break
    print("✅ FFmpeg 安装完成。")
    os.remove("ffmpeg.zip")
    subprocess.run(["rmdir", "/s", "/q", "ffmpeg_tmp"], shell=True)

