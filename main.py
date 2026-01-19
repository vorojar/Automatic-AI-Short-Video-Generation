
import os
import json
from config import *
from generator.audio import AudioGenerator
from generator.image import ImageGenerator
from generator.animation import AnimationGenerator
from generator.synthesis import VideoSynthesizer

class ScriptEngine:
    def __init__(self):
        pass

    def split_script(self, full_text):
        """
        全自动：将长文案切分为多场景，并自动生成视觉 Prompt。
        在真实生产中，这一步会交给 GPT-4 完成。
        """
        # 简单的基于标点的切分逻辑
        import re
        sentences = re.split(r'[。！？；]', full_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        scenes = []
        for s in sentences:
            # 简单的关键词匹配生成 Prompt（模拟 LLM 导演）
            prompt = "cinematic, 8k, highly detailed"
            if "效率" in s or "科技" in s:
                prompt = "futuristic technology, neon lights, high speed, " + prompt
            elif "创造" in s or "艺术" in s:
                prompt = "artistic creation, vibrant colors, cerebral, " + prompt
            else:
                prompt = "minimalist landscape, sunset, professional, " + prompt
            
            scenes.append({"text": s, "prompt": prompt})
        return scenes

def main():
    print("🚀 正在启动全自动视频生成系统...")
    
    # 从本地文件读取文案
    script_file = os.path.join(BASE_DIR, "script.txt")
    if not os.path.exists(script_file):
        print(f"❌ 错误：找不到文案文件 {script_file}，请先创建它。")
        return
        
    with open(script_file, "r", encoding="utf-8") as f:
        user_input_text = f.read().strip()
    
    if not user_input_text:
        print("⚠️ 警告：script.txt 文件内容为空。")
        return
    
    # 初始化引擎
    script_engine = ScriptEngine()
    audio_gen = AudioGenerator(EDGE_TTS_VOICE, MOCK_AUDIO)
    image_gen = ImageGenerator(ARK_API_KEY, mock_mode=MOCK_IMAGE)
    anim_gen = AnimationGenerator(VIDEO_RES, FPS)
    synth = VideoSynthesizer(VIDEO_RES.replace("x", ":"), FPS)

    # 1. 剧本自动化处理
    print(f"✍️ 正在解析长文案...")
    scenes_data = script_engine.split_script(user_input_text)

    scene_files = []

    print(f"🎬 开始处理 {len(scenes_data)} 个场景...")
    
    for i, scene in enumerate(scenes_data):
        print(f"  > 正在渲染场景 {i+1}/{len(scenes_data)}: {scene['text'][:15]}...")
        
        audio_path = os.path.join(ASSETS_DIR, f"audio_{i}.mp3")
        image_path = os.path.join(ASSETS_DIR, f"bg_{i}.jpg")
        anim_path = os.path.join(ASSETS_DIR, f"anim_{i}.mov")
        scene_output = os.path.join(SCENES_DIR, f"scene_{i}.mp4")

        # 1. 生成音频和时间轴
        timestamps, duration = audio_gen.generate_tts(scene['text'], i, audio_path)
        
        # 2. 生成视觉背景
        image_gen.generate_image(scene['prompt'], image_path, VIDEO_RES)
        
        # 3. 生成 Manim 文本动画 (传递准确的时间轴)
        anim_gen.create_text_animation(scene['text'], timestamps, anim_path)
        
        # 4. 单场景合成 (传递准确的时长)
        synth.merge_scene(image_path, audio_path, anim_path, scene_output, duration=duration)
        
        scene_files.append(scene_output)

    # 5. 最终合并
    final_video = os.path.join(OUTPUT_DIR, "final_video.mp4")
    print(f"🔗 正在合并所有场景至: {final_video}")
    synth.concatenate_scenes(scene_files, final_video)

    print("✅ 视频生成成功！快去 output 文件夹看看吧。")

if __name__ == "__main__":
    main()
