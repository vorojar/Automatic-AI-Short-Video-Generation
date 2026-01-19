
import os
import requests
import time
import subprocess
import json

class ImageGenerator:
    def __init__(self, api_key=None, model_id=None, base_url=None, mock_mode=False):
        self.api_key = api_key
        self.model_id = model_id
        self.base_url = base_url
        self.mock_mode = mock_mode

    def generate_image(self, prompt, output_path, resolution="1080x1920", full_config=None):
        """
        根据不同的 Provider 调用不同的生成逻辑
        full_config: {provider, api_key, model_id, base_url, local_path}
        """
        config = full_config or {}
        provider = config.get('provider', 'volcengine')
        
        # 如果开启了全局 Mock 模式，直接走 Mock
        if self.mock_mode:
            return self._generate_mock(prompt, output_path, resolution)

        try:
            if provider == 'openai':
                return self._generate_openai(prompt, output_path, resolution, config)
            elif provider == 'local_zimage':
                return self._generate_local(prompt, output_path, resolution, config)
            else:
                # 默认走火山引擎 (volcengine)
                return self._generate_volcengine(prompt, output_path, resolution, config)
        except Exception as e:
            print(f"      ⚠️ [{provider}] 生成失败: {e}")
            return self._generate_fallback(output_path, resolution)

    def _generate_volcengine(self, prompt, output_path, resolution, config):
        api_key = config.get('api_key') or self.api_key
        model_id = config.get('model_id') or self.model_id
        base_url = config.get('base_url') or self.base_url or "https://ark.cn-beijing.volces.com/api/v3/images/generations"
        
        print(f"      [Ark] 正在请求火山引擎: {prompt[:20]}...")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        # 报错提示：image size must be at least 3686400 pixels (即 1440 * 2560)
        size_map = {
            "1080x1920": "1440x2560", 
            "1920x1080": "2560x1440",
            "1080x1080": "1920x1920"
        }
        target_size = size_map.get(resolution, "1920x1920")

        payload = {
            "model": model_id,
            "prompt": f"电影质感, 极高画质, {prompt}",
            "response_format": "url",
            "size": target_size,
            "stream": False,
            "sequential_image_generation": "disabled"
        }
        
        response = requests.post(base_url, json=payload, headers=headers, timeout=60)
        if response.status_code != 200:
            print(f"      ❌ API Error: {response.text}")
        response.raise_for_status()
        
        res_data = response.json()
        image_url = res_data["data"][0]["url"]
        self._download_image(image_url, output_path)
        return output_path

    def _generate_openai(self, prompt, output_path, resolution, config):
        api_key = config.get('api_key')
        base_url = config.get('base_url') or "https://api.openai.com/v1/images/generations"
        model_id = config.get('model_id') or "dall-e-3"

        print(f"      [OpenAI] 正在请求 DALL-E: {prompt[:20]}...")
        
        headers = { "Authorization": f"Bearer {api_key}" }
        # OpenAI 的尺寸映射
        size_map = {
            "1080x1920": "1024x1792",
            "1920x1080": "1792x1024",
            "1080x1080": "1024x1024"
        }
        payload = {
            "model": model_id,
            "prompt": prompt,
            "n": 1,
            "size": size_map.get(resolution, "1024x1024")
        }
        
        response = requests.post(base_url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        image_url = response.json()["data"][0]["url"]
        self._download_image(image_url, output_path)
        return output_path

    def _generate_local(self, prompt, output_path, resolution, config):
        local_cmd = config.get('local_path', 'z-image')
        print(f"      [Local] 正在调用本地模型: {local_cmd}")
        
        # 假设 local_cmd 是一个可执行程序，接受 --prompt 和 --output
        # 例如: z-image --prompt "xxx" --output "/path/to/out.jpg" --size "1080x1920"
        try:
            cmd = [
                local_cmd, 
                "--prompt", prompt, 
                "--output", output_path,
                "--size", resolution
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            if os.path.exists(output_path):
                return output_path
            raise Exception("本地命令运行成功但未找到输出文件")
        except Exception as e:
            print(f"      ❌ 本地调用失败: {e}")
            raise

    def _download_image(self, url, path):
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(path, 'wb') as f:
            f.write(r.content)

    def _generate_mock(self, prompt, output_path, resolution):
        print(f"      [Mock] 模拟成像: {prompt[:20]}...")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x1a1a1a:s={resolution}:d=1",
            "-vframes", "1", output_path, "-loglevel", "quiet"
        ], check=True)
        return output_path

    def _generate_fallback(self, output_path, resolution):
        w, h = resolution.split("x")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", 
            f"gradients=s={w}x{h}:c0=0x2d1b4e:c1=0x1a365d:x0=0:x1=0:y0=0:y1={h}:d=1",
            "-vf", "vignette=angle=PI/4", "-vframes", "1", output_path, "-loglevel", "error"
        ])
        return output_path
