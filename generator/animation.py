
import os
import subprocess
import json
import re

class AnimationGenerator:
    # 预设风格配置
    SUBTITLE_PRESETS = {
        "classic_yellow": {
            "name": "经典黄白 (缩放)",
            "primary_color": "&H0000FFFF",  # 黄
            "base_color": "&H00FFFFFF",     # 白
            "effect": "zoom_pop",
            "outline_color": "&H00151515",
            "shadow_color": "&H80000000"
        },
        "modern_white": {
            "name": "现代极简 (平滑)",
            "primary_color": "&H0000FFFF",  # 激活时黄
            "base_color": "&H00FFFFFF",     # 基础白
            "effect": "karaoke_wipe",
            "outline_color": "&H00000000",
            "shadow_color": "&H60000000"
        },
        "vibrant_pink": {
            "name": "活力粉紫 (缩放)",
            "primary_color": "&H00FF00FF",  # 粉色
            "base_color": "&H00FFFFFF",
            "effect": "zoom_pop",
            "outline_color": "&H00151515",
            "shadow_color": "&H80000000"
        },
        "explode_shock": {
            "name": "炸裂冲击 (震撼)",
            "primary_color": "&H0000FFFF",  # 黄色冲击
            "base_color": "&H00FFFFFF",
            "effect": "explode",
            "outline_color": "&H000000FF",  # 红色描边增强力量感
            "shadow_color": "&H80000000"
        }
    }

    def __init__(self, resolution="1080x1920", fps=30):
        self.resolution = resolution
        self.fps = fps

    def prepare_subtitles(self, text, timestamps, output_ass_path, duration=3.0, style_id="classic_yellow", font_name="PingFang SC"):
        """根据预设样式生成 ASS 字幕"""
        preset = self.SUBTITLE_PRESETS.get(style_id, self.SUBTITLE_PRESETS["classic_yellow"])
        self._write_ass_file(text, timestamps, duration, output_ass_path, preset, font_name)
        return output_ass_path

    def _write_ass_file(self, full_text, timestamps, duration, ass_path, preset, font_name):
        try:
            w_res, h_res = map(int, self.resolution.split("x"))
        except:
            w_res, h_res = 1080, 1920
            
        # 1. 文本对齐 (保持原逻辑)
        tokens_raw = re.findall(r'[\u4e00-\u9fa5]|[a-zA-Z0-9\-\'\"]+|[，。！？；：\"“”]', full_text)
        if not tokens_raw: return

        whisper_start = timestamps[0].get("start", 0) if timestamps else 0
        time_span = max(0.1, duration - whisper_start)

        def get_weight(tok):
            if re.match(r'[\u4e00-\u9fa5]', tok): return 1.0
            if re.match(r'[，。！？；：\"“”]', tok): return 0.2
            return max(0.5, len(tok) * 0.4)

        total_weight = sum(get_weight(t) for t in tokens_raw)
        aligned = []
        curr = whisper_start
        for tok in tokens_raw:
            w = get_weight(tok)
            dur = (w / total_weight) * time_span if total_weight > 0 else 0.1
            aligned.append({"text": tok, "start": curr, "end": curr + dur})
            curr += dur

        # 2. 布局参数
        is_vertical = w_res < h_res
        font_size = int(h_res * (0.055 if is_vertical else 0.08))
        y_center = int(h_res * 0.72) if is_vertical else int(h_res * 0.82)
        spacing = -int(font_size * 0.12) 
        line_max_w = int(w_res * 0.85)
        line_height = int(font_size * 1.5)

        def get_tok_width(tok):
            if re.match(r'[\u4e00-\u9fa5]', tok): return int(font_size * 0.9)
            if re.match(r'[，。！？；：\"“”]', tok): return int(font_size * 0.4)
            return len(tok) * (font_size * 0.5)

        # 3. 分行逻辑
        lines = []
        curr_line = []
        curr_w = 0
        for item in aligned:
            w = get_tok_width(item['text'])
            if curr_w + w > line_max_w and curr_line:
                lines.append(curr_line)
                curr_line = []
                curr_w = 0
            curr_line.append({**item, "w": w})
            curr_w += w + spacing
        if curr_line:
            lines.append(curr_line)

        # 4. 计算坐标
        final_layout = []
        for row_idx, line in enumerate(lines):
            def get_gap(i):
                if i >= len(line) - 1: return 0
                is_punc = lambda x: re.match(r'[，。！？；：\"“”]', x)
                if is_punc(line[i]['text']) or is_punc(line[i+1]['text']):
                    return int(font_size * 0.05)
                return spacing

            line_w = sum(t['w'] for t in line)
            for i in range(len(line) - 1):
                line_w += get_gap(i)
            
            start_x = (w_res - line_w) / 2
            y_row = y_center + (row_idx - (len(lines)-1)/2) * line_height
            
            x_curr = start_x
            for i, t in enumerate(line):
                final_layout.append({**t, "x": x_curr + t['w']/2, "y": y_row})
                x_curr += t['w'] + get_gap(i)

        # 5. 构造 ASS 内容
        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w_res}
PlayResY: {h_res}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,{font_name},{font_size},{preset['base_color']},{preset['base_color']},{preset['outline_color']},{preset['shadow_color']},1,0,0,0,100,100,0,0,1,3,2,5,0,0,0,1
Style: Active,{font_name},{font_size},{preset['primary_color']},{preset['primary_color']},{preset['outline_color']},{preset['shadow_color']},1,0,0,0,100,100,0,0,1,4,3,5,0,0,0,1
"""

        body = "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        start_all_str = self._ms_to_ass_time(whisper_start * 1000)
        end_all_str = self._ms_to_ass_time(duration * 1000)
        TIMING_OFFSET_MS = 200

        for item in final_layout:
            x, y = item['x'], item['y']
            s_time_ms = max(0, item['start'] * 1000 - TIMING_OFFSET_MS)
            e_time_ms = max(0, item['end'] * 1000 - TIMING_OFFSET_MS)
            is_punc = re.match(r'[，。！？；：\"“”]', item['text'])
            
            if is_punc or preset['effect'] == 'none':
                body += f"Dialogue: 0,{start_all_str},{end_all_str},Base,,0,0,0,,{{\\pos({x:.1f},{y:.1f})}}{item['text']}\n"
            else:
                # 背景层避让
                if s_time_ms > 0:
                    body += f"Dialogue: 0,{self._ms_to_ass_time(0)},{self._ms_to_ass_time(s_time_ms)},Base,,0,0,0,,{{\\pos({x:.1f},{y:.1f})}}{item['text']}\n"
                if e_time_ms < duration * 1000:
                    body += f"Dialogue: 0,{self._ms_to_ass_time(e_time_ms)},{end_all_str},Base,,0,0,0,,{{\\pos({x:.1f},{y:.1f})}}{item['text']}\n"

                # 激活动画层
                s_str, e_str = self._ms_to_ass_time(s_time_ms), self._ms_to_ass_time(e_time_ms)
                if preset['effect'] == 'zoom_pop':
                    dur_ms = int(max(50, e_time_ms - s_time_ms))
                    p1, p2 = min(150, int(dur_ms * 0.4)), min(300, int(dur_ms * 0.8))
                    tags = "{\\pos(" + f"{x:.1f},{y:.1f}" + ")\\t(0," + str(p1) + ",\\fscx130\\fscy130)\\t(" + str(p1) + "," + str(p2) + ",\\fscx100\\fscy100)}"
                    body += f"Dialogue: 1,{s_str},{e_str},Active,,0,0,0,,{tags}{item['text']}\n"
                elif preset['effect'] == 'explode':
                    dur_ms = int(max(50, e_time_ms - s_time_ms))
                    # 炸裂效果：从100%快速放大到250%，同时透明度从不透明变为全透明
                    tags = "{\\pos(" + f"{x:.1f},{y:.1f}" + ")\\t(0," + str(dur_ms) + ",\\fscx250\\fscy250\\alpha&HFF&)}"
                    body += f"Dialogue: 1,{s_str},{e_str},Active,,0,0,0,,{tags}{item['text']}\n"
                elif preset['effect'] == 'karaoke_wipe':
                    # 模仿 K 帧效果的简化版：激活时间段变色
                    body += f"Dialogue: 1,{s_str},{e_str},Active,,0,0,0,,{{\\pos({x:.1f},{y:.1f})}}{item['text']}\n"

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header + body)

    def _ms_to_ass_time(self, ms):
        ms = max(0, int(ms))
        h, m, s, cs = ms // 3600000, (ms % 3600000) // 60000, (ms % 60000) // 1000, (ms % 1000) // 10
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def create_text_animation(self, *args, **kwargs):
        pass

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header + body)

    def _ms_to_ass_time(self, ms):
        ms = max(0, int(ms))
        h = ms // 3600000
        m = (ms % 3600000) // 60000
        s = (ms % 60000) // 1000
        cs = (ms % 1000) // 10
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def create_text_animation(self, *args, **kwargs):
        pass
