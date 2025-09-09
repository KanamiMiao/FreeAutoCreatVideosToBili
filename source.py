import requests
import os
import yaml
import logging
import json
import asyncio
import aiohttp
import aiofiles
from translate import Translator
import time
from typing import List, Dict, Any
import random
import math

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

config = {}
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

today = time.strftime("%Y-%m-%d", time.localtime(time.time()))
video_output_dir = f'{config["source_dir"]}/{today}/videos'
tags_dir = f'{config["source_dir"]}/{today}/tags.json'

tags_list = []
with open(tags_dir, 'r', encoding='utf-8') as f:
    tags_list = json.load(f)

# 全局会话对象
session = None

async def init_session():
    """初始化aiohttp会话"""
    global session
    if session is None:
        connector = aiohttp.TCPConnector(limit=10)  # 限制并发连接数
        session = aiohttp.ClientSession(connector=connector)

async def close_session():
    """关闭aiohttp会话"""
    global session
    if session is not None:
        await session.close()
        session = None

async def get_video_source(tag: str, video_save_path: str) -> str:
    """
    从Pexels API获取视频并保存到指定路径（异步版本）
    
    参数:
    tag (str): 搜索关键词
    video_save_path (str): 视频保存路径（包括文件名和扩展名）
    
    返回:
    str: 成功时返回保存的视频路径，失败时返回None
    """
    # 确保保存目录存在
    save_dir = os.path.dirname(video_save_path)
    if save_dir and not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    pexels_api_key = config['pexels_api_key']
    pexels_base_url = config['pexels_base_url']
    
    # 确保会话已初始化
    await init_session()
    
    # 查询参数 - 使用最大允许值
    params = {
        'query': tag,           # 搜索关键词
        'per_page': 80,         # 使用API允许的最大值
        'page': 1               # 页码
    }

    headers = {
        'Authorization': pexels_api_key
    }

    try:
        # 发送 GET 请求搜索视频
        async with session.get(pexels_base_url, headers=headers, params=params) as response:
            if response.status != 200:
                logger.error(f"请求失败，状态码：{response.status}")
                return None
                
            data = await response.json()
            logger.info(f"请求成功！找到 {data.get('total_results', 0)} 个结果。")
            
            # 检查是否有视频结果
            if not data.get('videos') or len(data['videos']) == 0:
                logger.warning("未找到相关视频")
                return None
            
            # 收集所有符合条件的视频及其文件
            candidate_videos = []
            
            for video in data['videos']:
                # 获取视频时长
                duration = video.get('duration', 0)
                
                # 跳过时长小于10秒的视频
                if duration < 10:
                    continue
                
                # 检查视频文件
                video_files = video.get('video_files', [])
                for file in video_files:
                    width = file.get('width', 0)
                    height = file.get('height', 0)
                    file_size = file.get('size', 0)  # 如果有文件大小信息
                    
                    # 只考虑宽度大于高度的视频
                    if width <= height:
                        continue
                    
                    # 只考虑分辨率不低于480p的视频文件
                    if min(width, height) < 480:
                        continue
                    
                    # 计算宽高比得分（越接近16/9得分越高）
                    aspect_ratio = width / height
                    target_ratio = 16 / 9
                    aspect_score = 1 / (1 + abs(aspect_ratio - target_ratio))
                    
                    # 计算综合得分（优先考虑接近16/9宽高比，其次考虑文件大小）
                    # 这里给宽高比得分更高的权重
                    composite_score = aspect_score * 1000 + (1 / (file_size + 1)) if file_size > 0 else aspect_score * 1000
                    
                    candidate_videos.append({
                        'video': video,
                        'file': file,
                        'duration': duration,
                        'width': width,
                        'height': height,
                        'file_size': file_size,
                        'aspect_score': aspect_score,
                        'composite_score': composite_score
                    })
            
            # 如果没有找到符合条件的视频
            if not candidate_videos:
                logger.info("未找到宽度>高度且分辨率≥480p的视频，尝试放宽条件...")
                
                # 放宽条件：只要求宽度>高度，不限制分辨率
                for video in data['videos']:
                    duration = video.get('duration', 0)
                    
                    # 跳过时长小于10秒的视频
                    if duration < 10:
                        continue
                    
                    video_files = video.get('video_files', [])
                    for file in video_files:
                        width = file.get('width', 0)
                        height = file.get('height', 0)
                        file_size = file.get('size', 0)
                        
                        # 只考虑宽度大于高度的视频
                        if width <= height:
                            continue
                        
                        # 计算宽高比得分
                        aspect_ratio = width / height
                        target_ratio = 16 / 9
                        aspect_score = 1 / (1 + abs(aspect_ratio - target_ratio))
                        
                        # 计算综合得分
                        composite_score = aspect_score * 1000 + (1 / (file_size + 1)) if file_size > 0 else aspect_score * 1000
                        
                        candidate_videos.append({
                            'video': video,
                            'file': file,
                            'duration': duration,
                            'width': width,
                            'height': height,
                            'file_size': file_size,
                            'aspect_score': aspect_score,
                            'composite_score': composite_score
                        })
            
            # 如果还是没有找到宽度>高度的视频
            if not candidate_videos:
                logger.info("未找到宽度>高度的视频，尝试使用任何方向的视频...")
                
                # 放宽条件：不考虑方向，只要求时长≥10秒
                for video in data['videos']:
                    duration = video.get('duration', 0)
                    
                    # 跳过时长小于10秒的视频
                    if duration < 10:
                        continue
                    
                    video_files = video.get('video_files', [])
                    for file in video_files:
                        width = file.get('width', 0)
                        height = file.get('height', 0)
                        file_size = file.get('size', 0)
                        
                        # 计算宽高比得分（如果是竖屏视频，得分会很低）
                        aspect_ratio = width / height
                        target_ratio = 16 / 9
                        aspect_score = 1 / (1 + abs(aspect_ratio - target_ratio))
                        
                        # 计算综合得分
                        composite_score = aspect_score * 1000 + (1 / (file_size + 1)) if file_size > 0 else aspect_score * 1000
                        
                        candidate_videos.append({
                            'video': video,
                            'file': file,
                            'duration': duration,
                            'width': width,
                            'height': height,
                            'file_size': file_size,
                            'aspect_score': aspect_score,
                            'composite_score': composite_score
                        })
            
            # 如果还是没有找到任何视频
            if not candidate_videos:
                logger.info("未找到时长≥10秒的视频，选择最接近10秒的视频")
                
                # 选择所有视频中时长最接近10秒的
                closest_duration_video = min(
                    data['videos'], 
                    key=lambda x: abs(x.get('duration', 0) - 10)
                )
                
                duration = closest_duration_video.get('duration', 0)
                video_files = closest_duration_video.get('video_files', [])
                
                # 选择文件大小最小的视频文件
                try:
                    selected_file = min(
                        video_files, 
                        key=lambda x: x.get('size', float('inf'))
                    )
                except:
                    selected_file = video_files[0] if video_files else None
                
                if not selected_file:
                    logger.error("未找到任何视频文件")
                    return None
                
                # 创建候选视频项
                candidate_videos = [{
                    'video': closest_duration_video,
                    'file': selected_file,
                    'duration': duration,
                    'width': selected_file.get('width', 0),
                    'height': selected_file.get('height', 0),
                    'file_size': selected_file.get('size', 0),
                    'aspect_score': 0,  # 无法计算宽高比得分
                    'composite_score': 0  # 无法计算综合得分
                }]
            
            # 从符合条件的视频中选择综合得分最高的
            try:
                selected = max(candidate_videos, key=lambda x: x['composite_score'])
            except:
                selected = candidate_videos[0]
            
            video_url = selected['file']['link']
            logger.info(f"选择视频: {selected['video'].get('url', 'N/A')}")
            logger.info(f"视频时长: {selected['duration']}秒")
            logger.info(f"视频分辨率: {selected['width']}x{selected['height']}")
            logger.info(f"宽高比: {selected['width']/selected['height']:.2f}:1")
            
            # 下载视频
            logger.info(f"下载视频: {video_url}")
            async with session.get(video_url) as video_response:
                if video_response.status != 200:
                    logger.error(f"视频下载失败，状态码：{video_response.status}")
                    return None
                
                # 使用aiofiles异步保存文件
                async with aiofiles.open(video_save_path, 'wb') as f:
                    async for chunk in video_response.content.iter_chunked(8192):
                        await f.write(chunk)
            
            logger.info(f"视频已保存到: {video_save_path}")
            return video_save_path
            
    except aiohttp.ClientError as e:
        logger.error(f"网络请求出错: {e}")
        return None
    except Exception as e:
        logger.error(f"发生错误: {e}")
        return None

def zn2en(text: str) -> str:
    """同步翻译函数"""
    try:
        translator = Translator(from_lang="zh", to_lang="en")
        translation = translator.translate(text)
        return translation
    except Exception as e:
        logger.error(f"翻译出错: {e}")
        return text  # 出错时返回原文本

async def async_zn2en(text: str) -> str:
    """异步翻译函数（在线程池中运行）"""
    loop = asyncio.get_event_loop()
    try:
        # 在线程池中运行同步翻译函数
        return await loop.run_in_executor(None, zn2en, text)
    except Exception as e:
        logger.error(f"异步翻译出错: {e}")
        return text

def create_folder(folder_dir: str):
    """创建文件夹"""
    try:
        os.makedirs(folder_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"创建文件夹失败: {e}")

async def process_tag(tags: Dict[str, Any], folder_dir: str, index: int, tag: str):
    """处理单个标签的异步函数"""
    try:
        tag_en = await async_zn2en(tag)  # 异步翻译
        video_save_path = f'{folder_dir}/{index}-{tag}-{tag_en}.mp4'
        result = await get_video_source(tag_en, video_save_path)
        return result
    except Exception as e:
        logger.error(f"处理标签 {tag} 时出错: {e}")
        return None

async def get_videos():
    """异步获取所有视频"""
    create_folder(video_output_dir)
    folder_dir_list = [f'{video_output_dir}/{i}' for i in range(len(tags_list))]
    for dir in folder_dir_list:
        create_folder(dir)
    
    # 创建所有任务
    tasks = []
    for tags, folder_dir in zip(tags_list, folder_dir_list):
        for index, tag in enumerate(tags['top10_tags']):
            # 为每个标签创建一个任务
            task = process_tag(tags, folder_dir, index, tag)
            tasks.append(task)
    
    # 限制并发数，避免过多请求
    semaphore = asyncio.Semaphore(config['pexels_max_concurrent'])  # 并发请求个数
    
    async def limited_task(task):
        async with semaphore:
            # 添加随机延迟，避免请求过于频繁
            await asyncio.sleep(random.uniform(config['pexels_sleep'], config['pexels_sleep']*2))
            return await task
    
    # 执行所有任务
    results = await asyncio.gather(*[limited_task(task) for task in tasks], return_exceptions=True)
    
    # 统计结果
    success_count = sum(1 for r in results if r is not None and not isinstance(r, Exception))
    logger.info(f"视频下载完成，成功: {success_count}, 失败: {len(results) - success_count}")
    
    return results

async def main():
    """异步主函数"""
    try:
        await init_session()
        results = await get_videos()
        return results
    finally:
        await close_session()

if __name__ == '__main__':
    # 运行异步主函数
    asyncio.run(main())