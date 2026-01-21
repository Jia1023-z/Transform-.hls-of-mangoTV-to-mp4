# Transform-.hls-of-mangoTV-to-mp4（HLS文件修复和拼接工具）

这是一个用于视频软件下载了芒果TV的视频后将hls片段拼接成mp4的 Python 工具。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg) ![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-green.svg) ![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

## 解决的问题

很多浏览器下载的 HLS 视频无法直接使用 FFmpeg 合并，通常存在以下问题：

1.  **文件分段混乱**：视频被切分为多个子文件夹，且文件名没有标准的 `.ts` 后缀（如 `0`, `1`, `0_ts`）。
2.  **伪装文件头**：为了防止外部播放器播放，`.ts` 切片的二进制头部被加入了 PNG 或 JPG 的图片数据（Fake Headers）。直接合并会导致 FFmpeg 报错 `Invalid data found when processing input`。
3.  **索引失效**：原本的 `.m3u8` 文件路径通常不匹配或缺失。

本工具不依赖 `.m3u8` 索引，直接通过**扫描文件二进制流**，自动去除伪装头，将分片拼接为完整的 MP4 文件。

## 主要功能

*   **递归扫描**：支持输入总目录，自动遍历所有层级的子文件夹寻找视频分片。
*   **去伪装头**：通过检测 `0x47` (TS Sync Byte) 同步字节，自动切除文件头部的伪装数据。
*   **二进制拼接**：将清洗后的 TS 片段直接在二进制层面拼接，容错率高，避免 FFmpeg 对坏片报错。
*   **无损封装**：默认调用 FFmpeg 的 Copy 模式，不进行重编码，速度快且不损失画质。

## 环境要求

*   **Python 3.8+**
*   **FFmpeg**：
    *   请确保系统中已安装 FFmpeg 并配置了环境变量。
    *   或者将 `ffmpeg.exe` 放置在脚本同级目录下的 `ffmpeg` 文件夹内。
    *   `builder.py` 用于下载并安装ffmpeg

## 使用方法

1.  克隆或下载本项目。
2.  确保依赖已就绪，运行主程序：
    ```bash
    python main.py
    ```
3.  在弹出的界面中：
    *   点击 **选择**，选中包含视频缓存文件夹的目录（支持选中父目录批量处理）。
    *   点击 **开始**。
4.  程序会在每个视频子文件夹的同级目录下生成对应的 `.mp4` 文件。
5.  `mergy.py` 合并MP4子片段


## 原理说明

常规的合并方法是让 FFmpeg 读取 M3U8 列表，但当分片文件头损坏时 FFmpeg 会拒绝工作。
本工具采用了更底层的方法：
1.  忽略文件后缀，读取文件夹内所有文件的二进制数据。
2.  定位第一个 `0x47` 字节，丢弃之前的数据。
3.  将清洗后的数据流直接追加写入到一个临时的 `.ts` 大文件中。
4.  最后调用 `ffmpeg -i temp.ts -c copy output.mp4` 进行容器封装。

## License

MIT License. 仅供个人学习和研究使用。
