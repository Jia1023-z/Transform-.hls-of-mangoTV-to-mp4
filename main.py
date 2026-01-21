import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from pathlib import Path
import re
import shutil

# === 1. 强力清洗并追加到大文件 ===
def append_cleaned_data(ts_path, output_handle, log_widget):
    """
    读取小TS文件，找到0x47同步头，清洗后直接写入 output_handle (大文件句柄)
    """
    try:
        with open(ts_path, 'rb') as f:
            data = f.read()
            
        if not data: return False # 空文件

        # 寻找第一个 0x47 (TS Sync Byte)
        start_pos = -1
        limit = min(5000, len(data)) # 只在前5KB找，避免全文扫描太慢
        
        for i in range(limit):
            if data[i] == 0x47:
                # 简单验证：防止误判，TS包长188，检查后面是否也是0x47
                # 如果文件太小不够验证，或者验证成功，都算找到
                if i + 188 >= len(data) or data[i+188] == 0x47:
                    start_pos = i
                    break
        
        if start_pos != -1:
            # 写入清洗后的数据
            output_handle.write(data[start_pos:])
            return True
        else:
            # 如果实在找不到0x47，死马当活马医，直接写入（也许是纯音频流）
            # log_widget.insert(tk.END, f"  ⚠️ {ts_path.name} 未找到头，强制拼接\n")
            output_handle.write(data)
            return True
            
    except Exception as e:
        log_widget.insert(tk.END, f"  ❌ 读取错误 {ts_path.name}: {e}\n")
        return False

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s.name)]

# === 2. 单个文件夹处理逻辑 (二进制拼接版) ===
def process_single_folder(folder_path, log_widget, mode):
    folder = Path(folder_path)
    
    # 定义输出文件名
    final_mp4 = folder.parent / f"{folder.name}.mp4"
    
    # 检查是否存在 (如果想强制覆盖，请注释掉下面两行)
    if final_mp4.exists() and final_mp4.stat().st_size > 1024:
        log_widget.insert(tk.END, f"⏩ 跳过已存在：{final_mp4.name}\n")
        return False

    # 收集文件
    all_files = [
        f for f in folder.iterdir() 
        if f.is_file() and f.suffix.lower() not in ['.m3u8', '.mp4', '.py', '.exe', '.bat', '.txt']
    ]
    if not all_files: return False

    all_files.sort(key=natural_sort_key)
    
    log_widget.insert(tk.END, f"📂 处理目录：{folder.name} ({len(all_files)}个分片)\n")
    log_widget.update()

    # --- 核心改变：创建临时大文件 ---
    temp_big_ts = folder / "temp_merged_source.ts"
    
    try:
        with open(temp_big_ts, 'wb') as merged_f:
            count = 0
            for f in all_files:
                if append_cleaned_data(f, merged_f, log_widget):
                    count += 1
                if count % 100 == 0:
                    log_widget.insert(tk.END, f"  ...已拼接 {count} 个分片\n")
                    log_widget.update()
        
        log_widget.insert(tk.END, f"  🔗 拼接完成，生成临时文件 {temp_big_ts.stat().st_size / 1024 / 1024:.2f} MB\n")
    except Exception as e:
        log_widget.insert(tk.END, f"❌ 拼接阶段失败: {e}\n")
        return False

    # --- 调用 FFmpeg 转换 ---
    log_widget.insert(tk.END, f"🎬 正在转码导出为 MP4 ({mode})...\n")
    log_widget.update()
    
    ffmpeg_path = Path(os.getcwd()) / "ffmpeg" / "ffmpeg.exe"
    
    # 这里直接输入大TS文件，容错率极高
    cmd = [str(ffmpeg_path), "-i", str(temp_big_ts)]
    
    if mode == "原画质 (极速)":
        cmd.extend(["-c", "copy", "-bsf:a", "aac_adtstoasc"])
    elif mode == "强制 1080P":
        cmd.extend(["-c:v", "libx264", "-preset", "fast", "-vf", "scale=1920:-2", "-c:a", "copy"])
    elif mode == "强制 720P":
        cmd.extend(["-c:v", "libx264", "-preset", "fast", "-vf", "scale=1280:-2", "-c:a", "copy"])

    cmd.extend(["-y", str(final_mp4)])
    
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    process = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
    
    # 清理临时大文件
    try: os.remove(temp_big_ts) 
    except: pass

    if process.returncode == 0:
        log_widget.insert(tk.END, f"✅ 成功生成：{final_mp4.name}\n----------------------\n")
        log_widget.see(tk.END)
        return True
    else:
        log_widget.insert(tk.END, f"❌ FFmpeg 失败: {process.stderr[-300:]}\n----------------------\n")
        return False

# === 3. 递归入口 ===
def start_processing():
    folder = folder_var.get()
    mode = mode_combobox.get()
    if not folder: return
    
    log_text.delete(1.0, tk.END)
    btn.config(state=tk.DISABLED, text="正在处理...")
    
    # 查找所有包含 m3u8 的文件夹（作为识别标准）
    root_path = Path(folder)
    target_dirs = set()
    
    # 策略：只要文件夹里有疑似视频分片文件（没有后缀的也算），就视为目标
    # 既然m3u8可能不靠谱，我们直接看文件夹
    # 遍历所有子目录
    for subdir in root_path.rglob("*"):
        if subdir.is_dir():
            # 如果文件夹名字包含 "hls"，或者里面有大量文件，就列入候选
            if "hls" in subdir.name.lower() or len(list(subdir.glob("*"))) > 5:
                # 排除根目录自己
                if subdir != root_path:
                    target_dirs.add(subdir)
    
    # 如果没找到，可能用户直接选的是子目录
    if not target_dirs:
        target_dirs.add(root_path)

    # 排序
    sorted_dirs = sorted(list(target_dirs), key=lambda x: natural_sort_key(x))
    
    log_text.insert(tk.END, f"📊 扫描到 {len(sorted_dirs)} 个潜在任务文件夹...\n")
    
    success_count = 0
    for d in sorted_dirs:
        # 跳过 dist, ffmpeg 这种工具文件夹
        if d.name in ['dist', 'ffmpeg', 'ffmpeg_tmp', '__pycache__']: continue
        
        try:
            if process_single_folder(d, log_text, mode):
                success_count += 1
        except Exception as e:
            log_text.insert(tk.END, f"❌ 未知错误 {d.name}: {e}\n")

    messagebox.showinfo("完成", f"处理结束！成功：{success_count}")
    btn.config(state=tk.NORMAL, text="开始处理")

# === GUI ===
def select_folder():
    f = filedialog.askdirectory()
    if f: folder_var.set(f)

root = tk.Tk()
root.title("HLS 暴力拼接工具 v6.0 (二进制版)")
root.geometry("850x600")

f = tk.Frame(root)
f.pack(pady=10)
tk.Label(f, text="视频总目录:").pack(side=tk.LEFT)
folder_var = tk.StringVar()
tk.Entry(f, textvariable=folder_var, width=40).pack(side=tk.LEFT, padx=5)
tk.Button(f, text="选择", command=select_folder).pack(side=tk.LEFT)

f2 = tk.Frame(root)
f2.pack(pady=5)
tk.Label(f2, text="模式:").pack(side=tk.LEFT)
mode_combobox = ttk.Combobox(f2, values=["原画质 (极速)", "强制 1080P", "强制 720P"], state="readonly")
mode_combobox.current(0)
mode_combobox.pack(side=tk.LEFT)

btn = tk.Button(root, text="🔥 开始暴力拼接", command=start_processing, bg="#ffab91", height=2)
btn.pack(fill=tk.X, padx=20, pady=5)

log_text = scrolledtext.ScrolledText(root)
log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

root.mainloop()
