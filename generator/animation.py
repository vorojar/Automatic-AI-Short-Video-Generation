
import os
import subprocess
import json
import re

class AnimationGenerator:
    def __init__(self, resolution="1080x1920", fps=30):
        self.resolution = resolution
        self.fps = fps

    def prepare_subtitles(self, text, timestamps, output_ass_path, duration=3.0):
        """
        生成带有“逐字放大”和“黄白配色”的高级 ASS 字幕。
        """
        self._write_ass_file(text, timestamps, duration, output_ass_path)
        return output_ass_path

    def _write_ass_file(self, full_text, timestamps, duration, ass_path):
        try:
            w_res, h_res = map(int, self.resolution.split("x"))
        except:
            w_res, h_res = 1080, 1920
            
        # 1. 文本与时间对齐
        tokens_raw = re.findall(r'[\u4e00-\u9fa5]|[a-zA-Z0-9\-\'\"]+|[，。！？；：\"“”]', full_text)
        if not tokens_raw: return

        whisper_start = timestamps[0].get("start", 0) if timestamps else 0
        # 修正：使用总时长 duration 而不是最后一个词的 end，确保动画覆盖整个片段，解决末尾吞字感
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
        # 核心优化：使用负间距抵消字体自带的空白
        spacing = -int(font_size * 0.12) 
        line_max_w = int(w_res * 0.85)
        line_height = int(font_size * 1.5)

        def get_tok_width(tok):
            # 汉字其实不需要占满整个 font_size，缩减到 0.9 倍更紧凑
            if re.match(r'[\u4e00-\u9fa5]', tok): return int(font_size * 0.9)
            if re.match(r'[，。！？；：\"“”]', tok): return int(font_size * 0.4)
            return len(tok) * (font_size * 0.5)

        # 3. 分行逻辑
        lines = []
        curr_line = []
        curr_w = 0
        for item in aligned:
            w = get_tok_width(item['text'])
            # 如果加上这个词超出了行宽，且当前行不是空的，就换行
            if curr_w + w > line_max_w and curr_line:
                lines.append(curr_line)
                curr_line = []
                curr_w = 0
            
            curr_line.append({**item, "w": w})
            curr_w += w + spacing
        
        if curr_line:
            lines.append(curr_line)

        # 4. 计算最终坐标（每行居中）
        final_layout = []
        for row_idx, line in enumerate(lines):
            # 核心逻辑：如果当前词或下一个词是标点，强制使用正向“呼吸间距”，否则使用负向“紧凑间距”
            def get_gap(i):
                if i >= len(line) - 1: return 0
                curr_txt = line[i]['text']
                next_txt = line[i+1]['text']
                is_punc = lambda x: re.match(r'[，。！？；：\"“”]', x)
                if is_punc(curr_txt) or is_punc(next_txt):
                    return int(font_size * 0.05) # 给标点留 5% 的呼吸位
                return spacing # 正常文字继续使用负间距收紧

            line_w = sum(t['w'] for t in line)
            for i in range(len(line) - 1):
                line_w += get_gap(i)
            
            start_x = (w_res - line_w) / 2
            y_offset = (row_idx - (len(lines)-1)/2) * line_height
            y_row = y_center + y_offset
            
            x_curr = start_x
            for i, t in enumerate(line):
                final_layout.append({
                    **t,
                    "x": x_curr + t['w']/2,
                    "y": y_row
                })
                x_curr += t['w'] + get_gap(i)

        # 5. 构造 ASS 内容
        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w_res}
PlayResY: {h_res}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,PingFang SC,{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H60000000,1,0,0,0,100,100,0,0,1,3,2,5,0,0,0,1
Style: Active,PingFang SC,{font_size},&H0000FFFF,&H0000FFFF,&H00151515,&H80000000,1,0,0,0,100,100,0,0,1,4,3,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        body = ""
        start_all_str = self._ms_to_ass_time(whisper_start * 1000)
        end_all_str = self._ms_to_ass_time(duration * 1000)

        # 激进感官对齐：将偏移量拉到 200ms，实现明显的“字幕拽着声音走”的律动感
        TIMING_OFFSET_MS = 200

        for item in final_layout:
            x, y = item['x'], item['y']
            # 应用偏移后的时间
            s_time_ms = max(0, item['start'] * 1000 - TIMING_OFFSET_MS)
            e_time_ms = max(0, item['end'] * 1000 - TIMING_OFFSET_MS)
            scene_end_ms = duration * 1000
            
            # 检查是否为标点符号
            is_punc = re.match(r'[，。！？；：\"“”]', item['text'])
            
            # 背景层渲染
            if is_punc:
                # 标点符号不参与高亮，全程保持白色静态
                body += f"Dialogue: 0,{start_all_str},{end_all_str},Base,,0,0,0,,{{\\pos({x:.1f},{y:.1f})}}{item['text']}\n"
            else:
                # 普通文字：仍然采用“避让”算法分段显示
                if s_time_ms > 0:
                    s_pad = self._ms_to_ass_time(0)
                    e_pad = self._ms_to_ass_time(s_time_ms)
                    body += f"Dialogue: 0,{s_pad},{e_pad},Base,,0,0,0,,{{\\pos({x:.1f},{y:.1f})}}{item['text']}\n"
                
                if e_time_ms < scene_end_ms:
                    s_pad = self._ms_to_ass_time(e_time_ms)
                    e_pad = self._ms_to_ass_time(scene_end_ms)
                    body += f"Dialogue: 0,{s_pad},{e_pad},Base,,0,0,0,,{{\\pos({x:.1f},{y:.1f})}}{item['text']}\n"

                # 激活动画层 (只有普通文字才有)
                s_str = self._ms_to_ass_time(s_time_ms)
                e_str = self._ms_to_ass_time(e_time_ms)
                dur_ms = int(max(50, e_time_ms - s_time_ms))
                p1, p2 = min(150, int(dur_ms * 0.4)), min(300, int(dur_ms * 0.8))
                
                trans = "{\\pos(" + f"{x:.1f},{y:.1f}" + ")\\t(0," + str(p1) + ",\\fscx130\\fscy130)\\t(" + str(p1) + "," + str(p2) + ",\\fscx100\\fscy100)}"
                body += f"Dialogue: 1,{s_str},{e_str},Active,,0,0,0,,{tags if 'tags' in locals() else trans}{item['text']}\n"

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
