import edge_tts
import asyncio
import yaml  
import time  
import json  
import os
  
base_dir = os.path.dirname(os.path.abspath(__file__))  
os.chdir(base_dir)  
  
config = {}  
try:  
    with open('config.yaml', 'r', encoding='utf-8') as f:  
        config = yaml.safe_load(f)  
except:  
    pass  
  
# config  
today = time.strftime("%Y-%m-%d", time.localtime(time.time()))  
texts_dir = f'{config["source_dir"]}/{today}/texts.json'  
outputs_dir = f'{base_dir}/{config["source_dir"]}/{today}/voices'  
  
# 获取文案列表和输出音频路径列表  
texts = []  
try:  
    with open(f'{config["source_dir"]}/{today}/texts.json', 'r', encoding='utf-8') as f:  
        texts = json.load(f)  
except:  
    pass  
  
voice_output_dir = [f'{outputs_dir}/{i}.mp3' for i in range(len(texts))]  
  
try:  
    os.makedirs(outputs_dir, exist_ok=True)  
except:  
    pass  
  
async def get_tts_voice(text, voice_output):
    try:  
        voice = "zh-CN-XiaoxiaoNeural"  # 选择中文语音
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(voice_output)  # 异步保存
        print(f"音频已保存至: {voice_output}")
        return voice_output
    except Exception as e:
        print(f"处理文本 '{text[:50]}...' 时发生错误: {e}")
        return None


async def main():
    # 创建所有任务的列表
    tasks = []
    for i, (text, output_path) in enumerate(zip(texts, voice_output_dir)):
        # 为每个文本创建一个异步任务
        task = asyncio.create_task(get_tts_voice(text, output_path))
        tasks.append(task)
    
    # 等待所有任务完成
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 检查结果
    success_count = sum(1 for r in results if r is not None and not isinstance(r, Exception))
    error_count = len(texts) - success_count
    
    print(f"处理完成! 成功: {success_count}, 失败: {error_count}")
  
if __name__ == '__main__':  
    asyncio.run(main())