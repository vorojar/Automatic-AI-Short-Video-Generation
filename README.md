# 🎬 Automatic AI Short Video Generation

这款工具可以根据一段文案，自动完成语音合成、图片生成、动态字幕制作和背景音乐合成，最终产出符合短视频潮流的高质量视频。

## ✨ 核心特性

- **高级 ASS 动态字幕**：
  - **Karaoke 逐字高亮**：文字随语音节奏实时变色放大。
  - **感官对齐优化**：视觉高亮提前 200ms，消除听觉延迟感，极度丝滑。
  - **智能排版**：支持多行自动换行、居中对齐、标点符号自动避让。
  - **防重叠算法**：高亮时背景字自动空显，解决字符重叠阴影。
- **音频系统**：
  - 集成 `Edge-TTS`，提供自然流畅的配音。
  - 自动添加 **300ms 呼吸余量**，解决英语单词结尾截断问题。
  - 支持 BGM 在视频末尾自动淡出。
- **现代化 Web 交互**：
  - 实时任务进度流展示。
  - 支持 BGM 在线试听与预览。
  - 支持多种视频比例切换（9:16、1:1、16:9）。
  - 一键终止生成进程。

## 🛠️ 技术栈

- **后端**: Python (Flask, Multiprocessing)
- **前端**: Vanilla JS, CSS (Premium Minimalist Design)
- **核心依赖**:
  - `FFmpeg`: 视频渲染与字幕压制
  - `faster-whisper`: 极速词级时间戳提取
  - `edge-tts`: 微软语音合成接口

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
# 请确保系统已安装 ffmpeg
```

### 2. 配置说明
在 `config.py` 中配置你的 API Key（用于后续接入的图像生成引擎）。

### 3. 运行项目
```bash
python server.py
```
访问 `http://localhost:8888` 即可开始创作。

## 📂 项目结构
```text
├── generator/         # 核心生成引擎 (语音、图像、字幕、合成)
├── web/               # 前端 UI 代码
├── server.py          # Flask 服务与异步进程管理
├── config.py          # 全局配置
└── output/            # 视频产出目录
```

## 📝 许可证
MIT License
