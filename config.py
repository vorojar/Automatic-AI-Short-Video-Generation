
import os

# Edge TTS 配置（完全免费）
EDGE_TTS_VOICE = "zh-CN-XiaoxiaoNeural"  # 晓晓（自然女声）
# 其他可选音色: zh-CN-YunxiNeural (云溪男声), zh-CN-XiaoyiNeural (小伊女声)

# 火山引擎方舟 Ark 图像生成
ARK_API_KEY = "ebfe5043-1471-4b56-aa51-a2ee5137af22"
ARK_MODEL_ID = "ep-20260119202359-x5pl2"
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
