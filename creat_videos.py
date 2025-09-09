import os
import glob
import yaml
import time
import gc
import psutil
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 加载配置 - 修复编码问题
config = {}
try:
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
except UnicodeDecodeError:
    try:
        with open('config.yaml', 'r', encoding='gbk') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        exit(1)
except Exception as e:
    print(f"读取配置文件失败: {e}")
    exit(1)

today = time.strftime("%Y-%m-%d", time.localtime())
voices_folder = f'{config["source_dir"]}/{today}/voices'
videos_folder = f'{config["source_dir"]}/{today}/videos'
videos_out_folder = f'{config["source_dir"]}/{today}/videos_out'

# 内存管理函数
def memory_usage():
    """返回当前内存使用量（MB）"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_usage(threshold=80):
    """检查内存使用是否超过阈值"""
    memory_percent = psutil.virtual_memory().percent
    if memory_percent > threshold:
        print(f"内存使用率过高: {memory_percent}%")
        return True
    return False

def resize_and_crop_video(clip, target_aspect_ratio=16/9):
    """
    调整视频尺寸并裁剪以保持16:9宽高比
    """
    # 获取视频原始宽高
    original_width, original_height = clip.size
    original_aspect_ratio = original_width / original_height
    
    # 计算目标尺寸
    if original_aspect_ratio > target_aspect_ratio:
        # 视频比目标更宽，需要裁剪左右两侧
        target_height = original_height
        target_width = int(target_height * target_aspect_ratio)
        
        # 如果调整后的宽度大于原始宽度，则需要先缩放
        if target_width > original_width:
            scale_factor = original_width / target_width
            target_width = original_width
            target_height = int(target_width / target_aspect_ratio)
            clip = clip.resize(height=target_height)
            
            # 现在裁剪上下部分
            crop_y = (clip.h - target_height) // 2
            return clip.crop(y1=crop_y, y2=crop_y + target_height)
        else:
            # 裁剪左右部分
            crop_x = (original_width - target_width) // 2
            return clip.crop(x1=crop_x, x2=crop_x + target_width)
    else:
        # 视频比目标更高，需要裁剪上下两侧
        target_width = original_width
        target_height = int(target_width / target_aspect_ratio)
        
        # 如果调整后的高度大于原始高度，则需要先缩放
        if target_height > original_height:
            scale_factor = original_height / target_height
            target_height = original_height
            target_width = int(target_height * target_aspect_ratio)
            clip = clip.resize(width=target_width)
            
            # 现在裁剪左右部分
            crop_x = (clip.w - target_width) // 2
            return clip.crop(x1=crop_x, x2=crop_x + target_width)
        else:
            # 裁剪上下部分
            crop_y = (original_height - target_height) // 2
            return clip.crop(y1=crop_y, y2=crop_y + target_height)

def concatenate_videos_with_audio(voice_path, source_dir, video_out_path):
    """
    同步拼接视频并以音频长度为基准
    """
    # 检查内存使用
    if check_memory_usage():
        print("内存使用率过高，等待释放...")
        time.sleep(5)
        gc.collect()
    
    try:
        # 获取音频文件
        audio_clip = AudioFileClip(voice_path)
        audio_duration = audio_clip.duration
        print(f"音频长度: {audio_duration} 秒, 当前内存使用: {memory_usage():.2f} MB")
        
        # 获取素材文件夹中的所有MP4文件并按文件名排序
        video_files = sorted(glob.glob(os.path.join(source_dir, "*.mp4")))
        if not video_files:
            print("素材文件夹中没有找到MP4文件")
            return None
        
        print(f"找到 {len(video_files)} 个视频文件")
        
        # 加载所有视频文件并关闭声音，同时调整尺寸
        video_clips = []
        for video_file in video_files:
            try:
                # 检查内存使用
                if check_memory_usage(85):
                    print("内存使用率过高，等待释放...")
                    time.sleep(3)
                    gc.collect()
                
                clip = VideoFileClip(video_file)
                clip = clip.without_audio()
                # 调整视频尺寸以保持16:9宽高比
                clip = resize_and_crop_video(clip)
                video_clips.append(clip)
                print(f"加载并调整视频: {os.path.basename(video_file)}, 时长: {clip.duration} 秒, 尺寸: {clip.size}, 内存使用: {memory_usage():.2f} MB")
                
                # 及时释放资源
                if len(video_clips) % 3 == 0:
                    gc.collect()
                    
            except Exception as e:
                print(f"加载视频 {video_file} 时出错: {e}")
        
        if not video_clips:
            print("没有成功加载任何视频")
            return None
        
        # 计算需要的视频总时长
        total_video_duration = 0
        needed_clips = []
        
        # 按顺序添加视频，直到总时长超过音频时长
        for clip in video_clips:
            if total_video_duration >= audio_duration:
                break
                
            needed_clips.append(clip)
            total_video_duration += clip.duration
        
        # 如果所有视频的总时长仍然不够，循环使用视频
        if total_video_duration < audio_duration:
            print(f"所有视频总时长 ({total_video_duration} 秒) 小于音频时长，将循环使用视频")
            
            # 计算还需要多少时长
            remaining_duration = audio_duration - total_video_duration
            
            # 从第一个视频开始循环添加，直到满足时长要求
            clip_index = 0
            while remaining_duration > 0 and video_clips:
                clip = video_clips[clip_index % len(video_clips)]
                
                # 如果当前视频时长大于剩余需要时长，则截取部分视频
                if clip.duration > remaining_duration:
                    partial_clip = clip.subclip(0, remaining_duration)
                    needed_clips.append(partial_clip)
                    remaining_duration = 0
                else:
                    needed_clips.append(clip)
                    remaining_duration -= clip.duration
                
                clip_index += 1
        
        print(f"将使用 {len(needed_clips)} 个视频片段进行拼接")
        
        # 拼接视频
        if len(needed_clips) == 1:
            final_clip = needed_clips[0]
        else:
            final_clip = concatenate_videoclips(needed_clips, "compose")
        
        # 设置音频
        final_clip = final_clip.set_audio(audio_clip)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(os.path.abspath(video_out_path)), exist_ok=True)
        
        # 输出视频
        print("正在输出视频...")
        
        # 输出视频
        final_clip.write_videofile(
            video_out_path,
            codec='libx264',
            audio_codec='aac',
            threads=2,
            preset='medium',
            ffmpeg_params=['-crf', '23'],
            verbose=False,
            logger=None
        )
        
        print(f"视频已保存到: {video_out_path}")
        return video_out_path
        
    except Exception as e:
        print(f"处理视频时出错: {e}")
        return None
    finally:
        # 确保释放资源
        try:
            audio_clip.close()
        except:
            pass
        
        for clip in video_clips:
            try:
                clip.close()
            except:
                pass
        
        try:
            final_clip.close()
        except:
            pass
        
        # 强制垃圾回收
        gc.collect()

def get_sorted_folders(folder_path):
    """
    获取文件夹中按数字顺序排序的子文件夹列表
    """
    # 获取所有子文件夹
    subfolders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
    
    # 按数字顺序排序
    try:
        subfolders.sort(key=lambda x: int(x))
    except ValueError:
        # 如果文件夹名不是纯数字，则按字母顺序排序
        subfolders.sort()
    
    return subfolders

def get_sorted_files(folder_path, extension=".mp3"):
    """
    获取文件夹中按数字顺序排序的文件列表
    """
    # 获取所有指定扩展名的文件
    files = [f for f in os.listdir(folder_path) if f.endswith(extension)]
    
    # 按数字顺序排序（基于文件名中的数字部分）
    try:
        files.sort(key=lambda x: int(os.path.splitext(x)[0]))
    except ValueError:
        # 如果文件名不是纯数字，则按字母顺序排序
        files.sort()
    
    return files

def process_single_video(i, audio_file, video_folder):
    """
    处理单个视频的同步函数
    """
    print(f"\n开始处理第 {i} 组: 音频 '{audio_file}' 和视频文件夹 '{video_folder}'")
    
    voice_path = os.path.join(voices_folder, audio_file)
    source_dir = os.path.join(videos_folder, video_folder)
    
    # 创建输出文件名
    output_filename = f"{i}.mp4"
    video_out_path = os.path.join(videos_out_folder, output_filename)
    
    # 处理视频
    result = concatenate_videos_with_audio(voice_path, source_dir, video_out_path)
    
    # 处理完成后强制垃圾回收
    gc.collect()
    
    print(f"完成第 {i} 组处理")
    return result

def main():
    """
    同步主函数
    """
    # 确保voices、videos和videos_out文件夹存在
    if not os.path.exists(voices_folder):
        print(f"音频文件夹不存在: {voices_folder}")
        return
    
    if not os.path.exists(videos_folder):
        print(f"视频文件夹不存在: {videos_folder}")
        return
    
    # 创建输出目录
    os.makedirs(videos_out_folder, exist_ok=True)
    
    # 获取按数字顺序排序的音频文件和视频文件夹
    audio_files = get_sorted_files(voices_folder, ".mp3")
    video_folders = get_sorted_folders(videos_folder)
    
    print(f"找到 {len(audio_files)} 个音频文件")
    print(f"找到 {len(video_folders)} 个视频文件夹")
    
    # 确保音频文件和视频文件夹数量匹配
    if len(audio_files) != len(video_folders):
        print(f"警告: 音频文件数量 ({len(audio_files)}) 与视频文件夹数量 ({len(video_folders)}) 不匹配")
        # 使用较小的数量
        min_count = min(len(audio_files), len(video_folders))
        audio_files = audio_files[:min_count]
        video_folders = video_folders[:min_count]
        print(f"将处理前 {min_count} 个匹配的文件和文件夹")
    
    # 逐个处理每个视频
    success_count = 0
    for i, (audio_file, video_folder) in enumerate(zip(audio_files, video_folders)):
        try:
            result = process_single_video(i, audio_file, video_folder)
            if result is not None:
                success_count += 1
        except Exception as e:
            print(f"处理第 {i} 组时出错: {e}")
    
    print(f"\n所有视频处理完成! 成功: {success_count}, 失败: {len(audio_files) - success_count}")

# 运行主函数
if __name__ == "__main__":
    main()