import os
import json
import uuid
import multiprocessing
import time
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS

app = Flask(__name__, static_folder='web', static_url_path='')
CORS(app)

# 任务文件路径
TASKS_FILE = os.path.join(os.getcwd(), "assets", "tasks.json")

def load_tasks_from_disk():
    if not os.path.exists(TASKS_FILE): return {}
    try:
        with open(TASKS_FILE, 'r') as f:
            return json.load(f)
    except: return {}

def save_task_to_disk(task_id, task_data):
    all_tasks = load_tasks_from_disk()
    all_tasks[task_id] = task_data
    os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
    with open(TASKS_FILE, 'w') as f:
        json.dump(all_tasks, f, indent=2)

# Edge TTS 可用音色
VOICES = [
    {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓 (女声)", "lang": "zh"},
    {"id": "zh-CN-YunxiNeural", "name": "云溪 (男声)", "lang": "zh"},
    {"id": "zh-CN-XiaoyiNeural", "name": "小艺 (女声)", "lang": "zh"},
    {"id": "zh-CN-YunjianNeural", "name": "云健 (男声)", "lang": "zh"},
    {"id": "zh-CN-XiaochenNeural", "name": "晓晨 (女声)", "lang": "zh"},
    {"id": "zh-CN-XiaohanNeural", "name": "晓涵 (女声)", "lang": "zh"},
]

RESOLUTIONS = {
    "9:16": "1080x1920",
    "16:9": "1920x1080",
    "1:1": "1080x1080",
}

def run_generation_process(task_id, text, voice, resolution, bgm="none", subtitle_style="classic_yellow", font_name="PingFang SC", image_config=None):
    """后台进程独立运行，内部使用线程池并行处理场景"""
    from concurrent.futures import ThreadPoolExecutor
    import threading
    import re
    import traceback
    from generator.audio import AudioGenerator
    from generator.image import ImageGenerator
    from generator.animation import AnimationGenerator
    from generator.synthesis import VideoSynthesizer
    
    try:
        print(f"[{task_id}] 🎬 引擎启动...")
        
        disk_lock = threading.Lock()

        def update_task_state(progress, status="running", scene_updates=None, video_path=None, error=None):
            """
            scene_updates 格式: { scene_id: { "text": "...", "step": "...", "done": bool } }
            """
            with disk_lock:
                try:
                    tasks = load_tasks_from_disk()
                    task = tasks.get(task_id, {})
                    
                    if status: task["status"] = status
                    if progress is not None: task["progress"] = progress
                    if video_path: task["video_path"] = video_path
                    if error: task["error"] = error
                    task["last_update"] = time.time()
                    
                    if "scenes_status" not in task: task["scenes_status"] = {}
                    if scene_updates:
                        for s_id, s_data in scene_updates.items():
                            s_id_str = str(s_id)
                            if s_id_str not in task["scenes_status"]:
                                task["scenes_status"][s_id_str] = s_data
                            else:
                                # 增量更新属性
                                task["scenes_status"][s_id_str].update(s_data)
                    
                    tasks[task_id] = task
                    with open(TASKS_FILE, 'w') as f:
                        json.dump(tasks, f, indent=2)
                except Exception as e:
                    print(f"Update state error: {e}")

        update_task_state(2, scene_updates={"0": {"text": "系统信息", "step": "正在预热音视频引擎...", "done": False}})
        res = RESOLUTIONS.get(resolution, "1080x1920")
        
        from config import ARK_API_KEY, ARK_MODEL_ID, MOCK_IMAGE
        
        # 优先使用前端传来的配置
        curr_api_key = ARK_API_KEY
        curr_model_id = ARK_MODEL_ID
        if image_config:
            if image_config.get('api_key'): curr_api_key = image_config['api_key']
            if image_config.get('model_id'): curr_model_id = image_config['model_id']

        audio_gen = AudioGenerator(voice, mock_mode=False)
        audio_gen._load_whisper() 
        image_gen = ImageGenerator(curr_api_key, model_id=curr_model_id, mock_mode=MOCK_IMAGE)
        anim_gen = AnimationGenerator(res, 30)
        synth = VideoSynthesizer(res.replace("x", ":"), 30)

        update_task_state(5, scene_updates={"0": {"step": "🚀 引擎预热完毕，准备流水线过程..."}})
        
        assets_dir = os.path.join(os.getcwd(), "assets")
        output_dir = os.path.join(os.getcwd(), "output")
        scenes_dir = os.path.join(assets_dir, "scenes")
        bgm_dir = os.path.join(assets_dir, "bgm")
        for d in [assets_dir, output_dir, scenes_dir, bgm_dir]: os.makedirs(d, exist_ok=True)
        
        sentences = re.findall(r'[^。！？；\n\r]+[。！？；\n\r]*[”"’\']?', text)
        sentences = [s.strip() for s in sentences if re.search(r'[\u4e00-\u9fa5a-zA-Z0-9]', s)]
        if not sentences: sentences = [text.strip()]
        
        total_scenes = len(sentences)
        scene_files = [None] * total_scenes
        completed_count = 0
        comp_lock = threading.Lock()
        whisper_lock = threading.Lock() 

        # 字幕参数已作为函数参数传入

        def process_single_scene(index, sentence):
            nonlocal completed_count
            scene_id = index + 1
            try:
                # 初始显示
                update_task_state(None, scene_updates={scene_id: {"text": sentence, "step": "🎙️ 正在合成配音...", "done": False}})
                
                audio_path = os.path.join(assets_dir, f"audio_{task_id}_{index}.mp3")
                with whisper_lock:
                    timestamps, duration = audio_gen.generate_tts(sentence, index, audio_path)

                update_task_state(None, scene_updates={scene_id: {"step": "🎨 正在绘制背景图..."}})
                image_path = os.path.join(assets_dir, f"bg_{task_id}_{index}.jpg")
                image_gen.generate_image(sentence, image_path, res, full_config=image_config)

                update_task_state(None, scene_updates={scene_id: {"step": "📐 正在生成动态字幕..."}})
                ass_path = os.path.join(assets_dir, f"anim_{task_id}_{index}.ass")
                anim_gen.prepare_subtitles(sentence, timestamps, ass_path, duration, style_id=subtitle_style, font_name=font_name)

                update_task_state(None, scene_updates={scene_id: {"step": "🎬 正在合成场景视频..."}})
                scene_output = os.path.join(scenes_dir, f"scene_{task_id}_{index}.mp4")
                synth.merge_scene(image_path, audio_path, ass_path, scene_output, duration=duration)

                scene_files[index] = scene_output
                
                with comp_lock:
                    completed_count += 1
                    current_pct = 5 + int((completed_count / total_scenes) * 80)
                    update_task_state(current_pct, scene_updates={scene_id: {"step": "已完成", "done": True}})
                
            except Exception as e:
                print(f"场景 {scene_id} 错误: {e}")
                update_task_state(None, scene_updates={scene_id: {"step": f"❌ 失败: {str(e)[:20]}", "done": False}})

        # 并发执行
        update_task_state(10, scene_updates={"0": {"step": "🏭 并行生产车间运转中..."}})
        with ThreadPoolExecutor(max_workers=2) as executor:
            for i, s in enumerate(sentences):
                executor.submit(process_single_scene, i, s)
                time.sleep(0.5)

        update_task_state(85, scene_updates={"0": {"step": "🎥 正在进行全局视频合并...", "done": False}})
        valid_scenes = [f for f in scene_files if f and os.path.exists(f)]
        
        temp_video = os.path.join(output_dir, f"temp_{task_id}.mp4")
        final_video = os.path.join(output_dir, f"video_{task_id}.mp4")
        synth.concatenate_scenes(valid_scenes, temp_video)
        
        if bgm != "none":
            update_task_state(95, scene_updates={"0": {"step": "🎵 正在智能混音...", "done": False}})
            bgm_path = os.path.join(bgm_dir, f"{bgm}.mp3")
            synth.add_background_music(temp_video, bgm_path, final_video)
            if os.path.exists(temp_video) and os.path.exists(final_video): os.remove(temp_video)
            elif not os.path.exists(final_video): os.rename(temp_video, final_video)
        else:
            if os.path.exists(temp_video): os.rename(temp_video, final_video)
        
        update_task_state(100, status="completed", video_path=final_video, scene_updates={"0": {"step": "✨ 所有任务已圆满完成！", "done": True}})
        
    except Exception as e:
        print(f"[{task_id}] 致命错误: {e}")
        traceback.print_exc()
        try:
            update_task_state(0, status="error", error=str(e))
        except: pass
    finally:
        # 清理临时文件 (更为激进的清理模式)
        print(f"[{task_id}] 🧹 正在清理现场...")
        import glob
        import shutil
        
        # 匹配所有包含 task_id 的临时文件
        patterns = [
            os.path.join(assets_dir, f"*{task_id}*"),
            os.path.join(scenes_dir, f"*{task_id}*"),
            os.path.join(output_dir, f"temp_{task_id}.mp4"),
        ]
        
        for pattern in patterns:
            for f in glob.glob(pattern):
                try:
                    if os.path.isfile(f):
                        os.remove(f)
                    elif os.path.isdir(f):
                        shutil.rmtree(f)
                    print(f"  - 自动清理: {os.path.basename(f)}")
                except Exception as e:
                    print(f"  - 清理失败 {f}: {e}")

@app.route('/')
def index(): return app.send_static_file('index.html')

@app.route('/api/voices')
def get_voices(): return jsonify(VOICES)

@app.route('/api/resolutions')
def get_resolutions():
    return jsonify([
        {"id": "9:16", "name": "竖屏 9:16 (抖音/短视频)"},
        {"id": "16:9", "name": "横屏 16:9 (B站/YouTube)"},
        {"id": "1:1", "name": "正方形 1:1"},
    ])

@app.route('/api/bgm')
def get_bgm_list():
    return jsonify([
        {"id": "none", "name": "无音乐"},
        {"id": "chill", "name": "安静思考 (Chill)"},
        {"id": "tech", "name": "动感科技 (Tech)"},
        {"id": "inspiring", "name": "昂扬向上 (Inspire)"},
    ])

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    text, voice, res, bgm = data.get('text', '').strip(), data.get('voice'), data.get('resolution'), data.get('bgm', 'none')
    if not text: return jsonify({"error": "请输入文案"}), 400
    
    subtitle_style = data.get('subtitle_style', 'classic_yellow')
    font_name = data.get('font_name', 'PingFang SC')
    image_config = data.get('image_config')
    
    task_id = str(uuid.uuid4())[:8]
    save_task_to_disk(task_id, {
        "status": "pending", "progress": 0, "scenes_status": {}, "video_path": None, "error": None, "last_update": time.time()
    })
    
    p = multiprocessing.Process(target=run_generation_process, args=(task_id, text, voice, res, bgm, subtitle_style, font_name, image_config))
    p.start()
    running_processes[task_id] = p
    return jsonify({"task_id": task_id})

@app.route('/api/progress/<task_id>')
def get_progress(task_id):
    def generate_events():
        while True:
            tasks = load_tasks_from_disk()
            if task_id not in tasks: break
            yield f"data: {json.dumps(tasks[task_id])}\n\n"
            if tasks[task_id]["status"] in ["completed", "error"]: break
            time.sleep(1)
    return Response(generate_events(), mimetype='text/event-stream')

@app.route('/api/download/<task_id>')
def download(task_id):
    tasks = load_tasks_from_disk()
    if task_id not in tasks or not tasks[task_id]["video_path"]: return jsonify({"error": "找不到文件"}), 404
    return send_file(tasks[task_id]["video_path"], as_attachment=True, download_name=f"ai_video_{task_id}.mp4")

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('assets', filename)

# 全局进程管理
running_processes = {}

@app.route('/api/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """获取任务状态和进程日志"""
    # Assuming temp_dir is defined elsewhere or should be derived from TASKS_FILE location
    # For this change, we'll assume it's meant to be a temporary directory for task states.
    # If temp_dir is not defined, this will cause a NameError.
    # For now, let's use the directory of TASKS_FILE as a placeholder for state files.
    temp_dir = os.path.dirname(TASKS_FILE) # Added this line to make the code syntactically correct
    state_file = os.path.join(temp_dir, f"{task_id}.json")
    if not os.path.exists(state_file):
        return jsonify({"status": "waiting", "scenes": {}})
    
    with open(state_file, "r") as f:
        return jsonify(json.load(f))

@app.route('/api/subtitle_presets', methods=['GET'])
def get_subtitle_presets():
    from generator.animation import AnimationGenerator
    return jsonify({
        "presets": [
            {"id": k, "name": v["name"]} for k, v in AnimationGenerator.SUBTITLE_PRESETS.items()
        ],
        "fonts": [
            "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Arial Unicode MS", "STHeiti"
        ]
    })
            
@app.route('/api/abort/<task_id>', methods=['POST'])
def abort_task(task_id):
    if task_id in running_processes:
        p = running_processes[task_id]
        if p.is_alive():
            p.terminate()
            p.join()
            print(f"[{task_id}] 🛑 任务已被用户强制中止")
        del running_processes[task_id]
    
    # 更新任务状态
    tasks = load_tasks_from_disk()
    if task_id in tasks:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = "任务已被用户中止"
        with open(TASKS_FILE, 'w') as f:
            json.dump(tasks, f, indent=2)
            
    return jsonify({"status": "aborted"})

from flask import send_from_directory

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888, threaded=True)
