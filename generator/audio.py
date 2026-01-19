
import os
import json
import subprocess
import asyncio

class AudioGenerator:
    def __init__(self, voice="zh-CN-XiaoxiaoNeural", mock_mode=False):
        """
        初始化音频生成器
        voice: Edge TTS 音色，默认使用晓晓（自然女声）
        """
        self.voice = voice
        self.mock_mode = mock_mode
        self.whisper_model = None
        
    def _load_whisper(self):
        """延迟加载 Faster-Whisper 模型"""
        if self.whisper_model is None:
            from faster_whisper import WhisperModel
            import torch
            
            # 自动检测 GPU
            if torch.cuda.is_available():
                device = "cuda"
                compute_type = "float16"
                print("      [Faster-Whisper] 检测到 NVIDIA GPU，使用 CUDA 加速")
            else:
                # Mac 环境推荐 CPU + int8 推理，速度极快
                device = "cpu"
                compute_type = "int8"
                print("      [Faster-Whisper] 使用 CPU 模式 (int8 优化)")
            
            # 加载模型（base 模型平衡速度和精度）
            # download_root 会自动处理模型下载
            self.whisper_model = WhisperModel("base", device=device, compute_type=compute_type)
        return self.whisper_model

    def generate_tts(self, text, scene_id, output_path):
        """
        使用 Edge TTS 生成语音，然后用 Faster-Whisper 提取精准时间戳
        """
        if self.mock_mode:
            return self._mock_generate(text, output_path)
        
        # 1. 使用 Edge TTS 生成音频
        try:
            print(f"      [Edge TTS] 正在合成语音: {text[:20]}...")
            asyncio.run(self._edge_tts_generate(text, output_path))
        except Exception as e:
            print(f"      ⚠️ Edge TTS 合成出错: {e}，切换到 Mock 模式")
            return self._mock_generate(text, output_path)
            
        if not os.path.exists(output_path):
            print("      ⚠️ Edge TTS 生成结果不存在，切换到 Mock 模式")
            return self._mock_generate(text, output_path)
        
        # 2. 使用 Faster-Whisper 提取精准时间戳
        print(f"      [Faster-Whisper] 正在提取词级时间戳...")
        try:
            timestamps, duration = self._extract_timestamps_with_whisper(output_path, text)
        except Exception as e:
            print(f"      ⚠️ Whisper 提取时间戳出错: {e}，使用估算时间")
            import traceback
            traceback.print_exc()
            duration = self._get_audio_duration(output_path)
            timestamps = self._simulate_timestamps(text, duration)
        
        return timestamps, duration

    async def _edge_tts_generate(self, text, output_path):
        """使用 edge-tts 异步生成语音，并添加 300ms 的静音缓冲防止截断"""
        import edge_tts
        
        communicate = edge_tts.Communicate(text, self.voice)
        temp_path = output_path + ".tmp.mp3"
        await communicate.save(temp_path)
        
        # 使用 FFmpeg 增加 0.3 秒静音缓冲
        # adelay 会导致整个音频推迟，我们这里使用 afilter 或者简单的拼接静音
        # 方案：在末尾增加 300ms 静音
        cmd = [
            "ffmpeg", "-y", "-i", temp_path,
            "-af", "apad=pad_dur=0.3", 
            "-c:a", "libmp3lame", "-b:a", "192k",
            output_path, "-loglevel", "error"
        ]
        subprocess.run(cmd, check=True)
        if os.path.exists(temp_path): os.remove(temp_path)

    def _extract_timestamps_with_whisper(self, audio_path, original_text):
        """使用 Faster-Whisper 提取词级时间戳，强制使用 ffprobe 获取准确时长"""
        model = self._load_whisper()
        
        segments, info = model.transcribe(
            audio_path,
            language="zh",
            word_timestamps=True,
            initial_prompt=original_text,
            beam_size=1
        )
        
        timestamps = []
        for segment in segments:
            if segment.words:
                for word_info in segment.words:
                    word = word_info.word.strip()
                    if word:
                        timestamps.append({
                            "word": word,
                            "start": word_info.start,
                            "end": word_info.end
                        })
        
        # 关键：使用 ffprobe 获取包含 pad 后的总时长
        duration = self._get_audio_duration(audio_path)
        
        if not timestamps:
            timestamps = self._simulate_timestamps(original_text, duration)
        
        return timestamps, duration

    def _mock_generate(self, text, output_path):
        """使用 Mac say 命令生成模拟配音"""
        print(f"      [Mock] 正在为内容生成模拟配音: {text[:15]}...")
        temp_aiff = output_path.replace(".mp3", ".aiff")
        subprocess.run(["say", "-v", "Tingting", text, "-o", temp_aiff])
        subprocess.run(["ffmpeg", "-y", "-i", temp_aiff, output_path, "-loglevel", "quiet"])
        if os.path.exists(temp_aiff):
            os.remove(temp_aiff)
        
        duration = self._get_audio_duration(output_path)
        timestamps = self._simulate_timestamps(text, duration)
        return timestamps, duration

    def _get_audio_duration(self, audio_path):
        """使用 ffprobe 获取音频时长"""
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True
        )
        try:
            return float(result.stdout.strip())
        except:
            return 3.0

    def _simulate_timestamps(self, text, total_duration):
        """基于字符均匀分配时间戳（fallback）"""
        import re
        tokens = re.findall(r'[\u4e00-\u9fa5]|[a-zA-Z0-9\-\']+', text)
        if not tokens:
            return []
        
        weights = [len(t) for t in tokens]
        total_weight = sum(weights)
        
        timestamps = []
        current_time = 0
        for i, tok in enumerate(tokens):
            duration = (weights[i] / total_weight) * total_duration
            timestamps.append({
                "word": tok,
                "start": current_time,
                "end": current_time + duration
            })
            current_time += duration
        
        return timestamps
