
import os

# Edge TTS 配置（完全免费）
EDGE_TTS_VOICE = "zh-CN-XiaoxiaoNeural"  # 晓晓（自然女声）
# 其他可选音色: zh-CN-YunxiNeural (云溪男声), zh-CN-XiaoyiNeural (小伊女声)

# 火山引擎方舟 Ark 图像生成 (建议通过 Web 界面配置，保存在浏览器缓存中)
ARK_API_KEY = ""
ARK_MODEL_ID = ""
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

# Project Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SCENES_DIR = os.path.join(ASSETS_DIR, "scenes")

# Video Settings
VIDEO_RES = "1080x1920"  # 9:16 default
FPS = 30

# Mock Settings
MOCK_AUDIO = False  # Edge TTS + Whisper: False (真实 API)
MOCK_IMAGE = False  # Seedream: False (真实 API)
