# 🎬 Automatic AI Short Video Generation

一款打破创作边界的 AI 短视频全自动生产工具。只需一段文案，即可完成从内容到成片的全部环节：语音合成、场景图绘、动态卡拉OK字幕、BGM 自动对仗。

![工作台截图](ScreenShot.png)

## ✨ 核心特性

- **多模态生图引擎**：
  - **跨厂商支持**：内置集成火山引擎 Ark (Doubao-SDXL)、OpenAI (DALL-E 3)。
  - **本地算力解放**：支持通过 CLI 调用本地模型（如 Z-Image），实现 0 成本生图。
  - **2K 超清画质**：自动适配各大模型的高画质分辨率要求（如 1440x2560）。
  - **客户端配置**：API Key 与模型参数完全由前端管理并持久化在本地缓存，安全灵活。

- **高级 ASS 动态字幕**：
  - **Karaoke 逐字高亮**：文字随语音节奏实时变色放大，支持多种预设风格（经典黄、现代白、炸裂冲击等）。
  - **感官对齐优化**：视觉高亮提前 200ms，消除听觉延迟感，极其丝滑。
  - **智能排版**：支持多行自动换行、居中对齐、标点符号自动避让。
  - **防重叠算法**：高亮时重构图层逻辑，解决 ASS 字符重叠阴影问题。

- **音频系统**：
  - 集成 `Edge-TTS`，提供自然流畅的配音，并支持词级时间戳提取。
  - 自动添加 **300ms 呼吸余量**，解决英文单词结尾截断的顽疾。
  - BGM 支持在线试听、音量平衡及片尾自动淡出。

- **现代化 Web 交互**：
  - **实时进度流**：每一个镜头的生成状态、生图进度实时反馈。
  - **全能配置面板**：实时调节视频比例、音色、字幕样式、字体及模型 API。
  - **一键生产控制**：支持实时中止任务，保护算力资源。

## 🛠️ 技术栈

- **后端**: Python (Flask, Multiprocessing, ThreadPool)
- **前端**: Vanilla JS, Tailwind CSS (Premium Minimalist Design)
- **核心依赖**:
  - `FFmpeg`: 视频多轨道合成与字幕硬压
  - `faster-whisper`: 高性能词级时间戳定位
  - `edge-tts`: 微软云语音合成引擎

## 🚀 快速开始

### 1. 环境准备
```bash
# 克隆项目并安装依赖
pip install -r requirements.txt
# 请确保系统已安装 ffmpeg (建议版本 >= 5.0)
```

### 2. 运行项目
```bash
python server.py
```
访问 `http://localhost:8888` 即可进入工作台。

### 3. 配置模型
点击右上角的 **「模型配置」** 按钮，填入您的 API Key 或本地模型路径。所有配置将保存在您的浏览器本地缓存中。

## 📂 项目结构
```text
├── generator/         # 核心生成引擎 (audio.py, image.py, animation.py, synthesis.py)
├── web/               # 现代化 Web UI
├── server.py          # 异步任务调度与 Flask 接口
├── config.py          # 系统级默认配置
└── output/            # 视频最终产出目录
```

## 📝 许可证
MIT License
