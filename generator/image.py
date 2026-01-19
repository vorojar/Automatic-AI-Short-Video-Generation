
import os
import requests
import time
import subprocess

class ImageGenerator:
    def __init__(self, api_key, mock_mode=True):
        self.api_key = api_key
        self.mock_mode = mock_mode
        self.api_url = "https://api.seedream.ai/v1/images/generations" # 示例端点，根据实际文档调整

    def generate_image(self, prompt, output_path, resolution="1080x1920"):
        if self.mock_mode:
            print(f"      [Mock] 正在模拟生成图像: {prompt[:20]}...")
            color = "0x2c3e50" if "tech" in prompt.lower() else "0x1a1a1a"
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c={color}:s={resolution}:d=1",
                "-vframes", "1",
                output_path,
                "-loglevel", "quiet"
            ], check=True, stdin=subprocess.DEVNULL)
            return output_path
        
        print(f"      [API] 正在通过 Seedream 生成图像: {prompt[:30]}...")
        # 实际 API 调用逻辑
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "prompt": prompt,
            "size": resolution,
            "model": "seedream-4.5"
        }
        
        try:
            # 这里根据 Seedream 官方文档的实际响应结构进行解析
            # 暂时假设它返回一个包含 URL 的 JSON
            response = requests.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            image_url = response.json()["data"][0]["url"]
            
            # 下载图片
            img_data = requests.get(image_url).content
            with open(output_path, 'wb') as f:
                f.write(img_data)
            return output_path
        except Exception as e:
            print(f"      ⚠️ Seedream 生成失败，切换到高质感电影背景: {e}")
            w, h = resolution.split("x")
            
            # 使用 gradients 滤镜生成可见的渐变背景
            # 从深紫 (顶部) 到深蓝 (底部)
            gradient_cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", 
                f"gradients=s={w}x{h}:c0=0x2d1b4e:c1=0x1a365d:x0=0:x1=0:y0=0:y1={h}:d=1",
                "-vf", "vignette=angle=PI/4,noise=alls=5:allf=t+u",
                "-vframes", "1",
                output_path,
                "-loglevel", "error"
            ]
            result = subprocess.run(gradient_cmd, capture_output=True)
            
            # 如果 gradients 滤镜不可用，使用更简单的方案
            if result.returncode != 0:
                simple_cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi", "-i", f"color=c=0x1e3a5f:s={w}x{h}:d=1",
                    "-vf", "vignette=angle=PI/3,noise=alls=8:allf=t+u",
                    "-vframes", "1",
                    output_path,
                    "-loglevel", "error"
                ]
                subprocess.run(simple_cmd)
            
            return output_path
