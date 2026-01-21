import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path
import re
from collections import defaultdict

# === 1. 自然排序 (保证 _0_29 排在 _30_59 前面) ===
def natural_sort_key(file_path):
    s = file_path.name
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

# === 2. 核心逻辑 ===
def smart_merge_groups():
    folder = folder_var.get()
    if not folder:
        messagebox.showwarning("提示", "请先选择文件夹")
        return

    root_path = Path(folder)
    log_text.delete(1.0, tk.END)
    btn.config(state=tk.DISABLED, text="正在智能处理中...")
    root.update()

    log_text.insert(tk.END, f"🔍 正在扫描 {root_path} 下的所有文件...\n")

    # 1. 递归找到所有 MP4
    all_mp4s = list(root_path.rglob("*.mp4"))
    
    # 2. 智能分组
    # 逻辑：读取文件名，以 ".hls" 为界限，前面的部分就是 ID
    groups = defaultdict(list)
    
    for mp4 in all_mp4s:
        # 过滤掉不是我们生成的切片文件 (文件名不含 .hls 的跳过)
        # 同时也过滤掉最终生成的大文件，防止死循环
        if ".hls" not in mp4.name or "_Full_Merged" in mp4.name:
            continue
            
        # 提取 ID: 比如 "Code.0.hls_0_29.mp4" -> ID 为 "Code.0"
        # split(".hls") 会把文件名切成两半，我们取第一半作为身份证
        series_id = mp4.name.split(".hls")[0]
        groups[series_id].append(mp4)

    if not groups:
        log_text.insert(tk.END, "❌ 未找到符合格式 (含.hls) 的分段视频。\n请确认上一部操作生成的MP4是否在目录下。\n")
        btn.config(state=tk.NORMAL, text="开始智能合并")
        return

    log_text.insert(tk.END, f"📊 识别到 {len(groups)} 部不同的视频，开始逐一合并...\n\n")

    # 3. 遍历每一组进行合并
    success_count = 0
    ffmpeg_path = Path(os.getcwd()) / "ffmpeg" / "ffmpeg.exe"

    for series_id, files in groups.items():
        log_text.insert(tk.END, f"🎬 正在处理系列：{series_id} (共 {len(files)} 个片段)\n")
        
        # 排序 (非常重要)
        files.sort(key=natural_sort_key)
        
        # 打印一下顺序给用户看，放心
        # for f in files: log_text.insert(tk.END, f"    - {f.name}\n")

        # 生成 list.txt
        list_path = root_path / f"temp_list_{series_id}.txt"
        with open(list_path, "w", encoding="utf-8") as f:
            for mp4 in files:
                safe_path = str(mp4.absolute()).replace("\\", "/")
                f.write(f"file '{safe_path}'\n")

        # 定义输出文件名：直接用 ID 命名
        final_output = root_path / f"{series_id}_Full_Merged.mp4"
        
        # 如果文件已存在，跳过（或者你可以改为覆盖）
        if final_output.exists():
            log_text.insert(tk.END, f"  ⏩ 文件已存在，跳过: {final_output.name}\n\n")
            try: os.remove(list_path)
            except: pass
            continue

        # FFmpeg 拼接
        cmd = [
            str(ffmpeg_path), "-f", "concat", "-safe", "0", 
            "-i", str(list_path), "-c", "copy", "-y", str(final_output)
        ]
        
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        process = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
        
        # 清理列表
        try: os.remove(list_path)
        except: pass

        if process.returncode == 0:
            log_text.insert(tk.END, f"  ✅ 合并成功！输出：{final_output.name}\n\n")
            log_text.see(tk.END)
            log_text.update()
            success_count += 1
        else:
            log_text.insert(tk.END, f"  ❌ 合并失败: {process.stderr[-200:]}\n\n")

    messagebox.showinfo("完成", f"所有任务结束！\n成功合并视频数: {success_count}")
    btn.config(state=tk.NORMAL, text="开始智能合并")

# === GUI ===
def select_folder():
    f = filedialog.askdirectory()
    if f: folder_var.set(f)

root = tk.Tk()
root.title("智能分组视频合并工具 v8.0")
root.geometry("800x600")

f = tk.Frame(root)
f.pack(pady=10)
tk.Label(f, text="视频总目录:").pack(side=tk.LEFT)
folder_var = tk.StringVar()
tk.Entry(f, textvariable=folder_var, width=50).pack(side=tk.LEFT, padx=5)
tk.Button(f, text="📂 选择", command=select_folder).pack(side=tk.LEFT)

btn = tk.Button(root, text="🧩 开始智能分组并合并", command=smart_merge_groups, bg="#b2dfdb", height=2)
btn.pack(fill=tk.X, padx=20, pady=5)

log_text = scrolledtext.ScrolledText(root, font=("Consolas", 9))
log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

root.mainloop()
