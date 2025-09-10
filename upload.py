from bilibili_api import video_uploader  
from bilibili_api.utils.network import Credential  
from bilibili_api.utils.picture import Picture  
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import asyncio
import yaml
import time
import json
import glob
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

config = {}
with open('config.yaml', 'r', encoding='utf-8') as f:  
    config = yaml.safe_load(f)  

today = time.strftime('%Y-%m-%d', time.localtime())
videos_folder = f'{config["source_dir"]}/{today}/videos_out'
videos = sorted(glob.glob(os.path.join(videos_folder, "*.mp4")))

datas_folder = f'{config["source_dir"]}/{today}/tags.json'
datas = []
with open(datas_folder, 'r', encoding='utf-8') as f:
    datas = json.load(f)
print(datas)



async def cookie2dict(cookie:str) -> dict:
    cookie_dict = {}
    cookie = cookie.split(';')
    for item in cookie:
        item = item.split('=')
        key = item[0].replace(' ','').lower()
        value = item[1]
        cookie_dict[key] = value
    return cookie_dict


def generate_cover_from_video(video_path: str, time_position: float = 5.0) -> Picture:  
    """  
    从视频中截取一帧作为封面，直接返回 Picture 对象  
      
    Args:  
        video_path: 视频文件路径  
        time_position: 截取时间点（秒），默认第5秒  
      
    Returns:  
        Picture: 封面图片对象  
    """  
    try:  
        # 加载视频  
        video = VideoFileClip(video_path)  
          
        # 确保时间点不超过视频长度  
        if time_position > video.duration:  
            time_position = video.duration / 2  
          
        # 截取指定时间的帧  
        frame = video.get_frame(time_position)  
          
        # 转换为 PIL Image  
        from PIL import Image  
        import io  
        img = Image.fromarray(frame)  
          
        # 转换为字节数据  
        img_bytes = io.BytesIO()  
        img.save(img_bytes, format='JPEG', quality=95)  
        img_bytes.seek(0)  
          
        video.close()  
          
        # 直接创建 Picture 对象  
        return Picture.from_content(img_bytes.getvalue(), 'jpg')  
          
    except Exception as e:  
        print(f"生成封面失败: {e}")  
        return None  
  
async def upload2bili(video_path, data):  
    cookie = await cookie2dict(config['bili_cookie'])  
      
    credential = Credential(  
        sessdata=cookie['sessdata'],  
        bili_jct=cookie['bili_jct'],  
        buvid3=cookie['buvid3'],  
        dedeuserid=cookie['dedeuserid']  
    )  
      
    # 直接生成 Picture 对象  
    cover = generate_cover_from_video(video_path)  
      
    if not cover:  
        raise Exception("封面生成失败")  
      
    # 创建视频元数据  
    meta = video_uploader.VideoMeta(  
        tid=data['typeid'],  
        title=data['title'],  
        desc=data['description'],  
        cover=cover,  # 直接使用 Picture 对象  
        tags=data['tags'],  
        original=True  
    ) 
    
    # 创建视频分P  
    page = video_uploader.VideoUploaderPage(  
        path=video_path,  
        title=data['title'],  
        description=data['description']  
    )  
    
    # 创建上传器  
    uploader = video_uploader.VideoUploader(  
        pages=[page],  
        meta=meta,  
        credential=credential  
    )  
    
    # 开始上传  
    result = await uploader.start()  
    print(f"上传成功！BVID: {result['bvid']}")

async def main():
    for video_path, data in zip(videos, datas):
        try:
            upload2bili(video_path, data)
        except Exception as e:
            print(f'上传B站失败：{e}')


if __name__ == '__main__':
    asyncio.run(main())