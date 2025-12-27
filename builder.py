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

# === 2️⃣ 生成主程序 hls_merger_tool.py ===
def create_main_script():
    code = r'''
import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path

def run_ffmpeg(input_m3u8, output_mp4):
    ffmpeg_path = Path(os.getcwd()) / "ffmpeg" / "ffmpeg.exe"
    cmd = [str(ffmpeg_path), "-allowed_extensions", "ALL", "-i", str(input_m3u8), "-c", "copy", str(output_mp4)]
    process = subprocess.run(cmd, capture_output=True, text=True)
    return process.returncode, process.stdout + process.stderr

def merge_hls_in_folder(folder_path, log_widget):
    folder = Path(folder_path)
    for sub in folder.iterdir():
        if sub.is_dir():
            m3u8_files = list(sub.glob("*.m3u8"))
            if not m3u8_files:
                continue
            m3u8 = m3u8_files[0]
            output = sub.with_suffix(".mp4")
            log_widget.insert(tk.END, f"正在合并：{m3u8.name} -> {output.name}\n")
            log_widget.update()
            code, log = run_ffmpeg(m3u8, output)
            if code == 0:
                log_widget.insert(tk.END, f"✅ 合并完成：{output}\n\n")
            else:
                log_widget.insert(tk.END, f"❌ 出错：{log}\n\n")

def select_folder():
    folder = filedialog.askdirectory(title="选择包含HLS文件夹的目录")
    if folder:
        folder_var.set(folder)

def start_merge():
    folder = folder_var.get()
    if not folder:
        messagebox.showwarning("提示", "请先选择一个文件夹！")
        return
    log_text.delete(1.0, tk.END)
    merge_hls_in_folder(folder, log_text)
    messagebox.showinfo("完成", "所有文件夹处理完成！")

root = tk.Tk()
root.title("HLS 批量合并工具 by CodeGPT")
root.geometry("700x500")

tk.Label(root, text="选择包含 .m3u8 的主目录：").pack(pady=5)
folder_var = tk.StringVar()
tk.Entry(root, textvariable=folder_var, width=70).pack(pady=5)
tk.Button(root, text="选择文件夹", command=select_folder).pack(pady=5)
tk.Button(root, text="开始合并", command=start_merge).pack(pady=5)

log_text = scrolledtext.ScrolledText(root, width=80, height=20)
log_text.pack(padx=10, pady=10)

root.mainloop()
    '''
    with open("hls_merger_tool.py", "w", encoding="utf-8") as f:
        f.write(code)
    print("✅ 主程序已生成：hls_merger_tool.py")

# === 3️⃣ 打包为 .exe ===
def build_exe():
    print("📦 开始打包为 .exe ...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    subprocess.run(["pyinstaller", "--onefile", "--noconsole", "hls_merger_tool.py"], check=True)
    print("✅ 打包完成，输出文件在 dist/HLS_Merger.exe")

if __name__ == "__main__":
    download_ffmpeg()
    create_main_script()
    build_exe()
    print("\n🚀 完成！请在 dist 文件夹中找到 HLS_Merger.exe，双击运行即可。")
