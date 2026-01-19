
import os
import subprocess

class VideoSynthesizer:
    def __init__(self, resolution="1080:1920", fps=30):
        self.resolution = resolution
        self.fps = fps

    def merge_scene(self, image_path, audio_path, ass_path, output_path, duration=3.0):
        """
        核心渲染引擎：将背景图片（Ken Burns）、音频和动态 ASS 字幕合成为一个场景。
        """
        w, h = self.resolution.split(":")
        total_frames = int(duration * self.fps)
        
        # Ken Burns effect: Zoom In + 强制重置时间基准防止漂移
        kb_filter = f"scale=1080:-1,zoompan=z='min(zoom+0.0005,1.2)':d={total_frames}:s={w}x{h}:fps={self.fps},setpts=PTS-STARTPTS"
        
        # 分离路径处理
        safe_ass_path = ass_path.replace("\\", "/").replace(":", "\\:")
        
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,      # 背景图
            "-i", audio_path,                    # 配音
            "-filter_complex",
            f"[0:v]{kb_filter},subtitles='{safe_ass_path}':force_style='Alignment=2'[outv]",
            "-map", "[outv]",
            "-map", "1:a",
            "-c:v", "h264_videotoolbox", "-b:v", "4000k", "-preset", "ultrafast", 
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{duration:.2f}",             # 精准时长
            output_path,
            "-loglevel", "error"
        ]
        
        subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL)

    def concatenate_scenes(self, scene_files, final_output):
        # Create a concat list
        list_file = "scenes.txt"
        with open(list_file, "w") as f:
            for scene in scene_files:
                f.write(f"file '{scene}'\n")
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", list_file,
            "-c", "copy",
            final_output,
            "-loglevel", "error"
        ]
        
        subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL)
        os.remove(list_file)

    def add_background_music(self, video_path, bgm_path, output_path, bgm_volume=0.3):
        """
        Mixes background music with sidechain ducking.
        """
        if not os.path.exists(bgm_path):
            print(f"      ⚠️ BGM 文件不存在: {bgm_path}, 跳过混音")
            if video_path != output_path:
                os.rename(video_path, output_path)
            return

        print(f"      [Audio] 正在进行智能混音 (Ducking)...")
        # -stream_loop -1: 循环 BGM 直到视频结束
        # sidechaincompress: 人声大时 BGM 自动变小
        # afade: 结尾 2 秒淡出
        filter_complex = (
            f"[1:a]volume={bgm_volume}[music];"
            f"[0:a]asplit[vocal][trigger];"
            f"[music][trigger]sidechaincompress=threshold=0.1:ratio=20:attack=100:release=800,afade=t=out:st=ST_PLACEHOLDER:d=2[music_ducked];"
            f"[vocal][music_ducked]amix=inputs=2:duration=first[outa]"
        )
        
        # 获取视频时长以便设置淡出起始点
        video_dur = self._get_video_duration(video_path)
        fade_start = max(0, video_dur - 2)
        filter_complex = filter_complex.replace("ST_PLACEHOLDER", f"{fade_start:.2f}")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-stream_loop", "-1", "-i", bgm_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[outa]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
            "-loglevel", "error"
        ]
        
        subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL)

    def _get_video_duration(self, video_path):
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True
        )
        try:
            return float(result.stdout.strip())
        except:
            return 0
