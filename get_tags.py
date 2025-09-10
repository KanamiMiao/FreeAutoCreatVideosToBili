import time
import asyncio
import os
import yaml
import pandas as pd
import logging
import ast
import json
from sklearn.preprocessing import MinMaxScaler
from collections import Counter
import re

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 读取配置文件
config = {}
try:
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
except Exception as e:
    logger.error(f"读取配置文件失败: {e}")
    exit(1)

# 全局变量
dataset_dir = config['dataset_dir']
source_dir = config['source_dir']

async def process_dataset(dataset_path):
    """处理单个数据集的异步函数"""
    try:
        # 读取数据
        df = pd.read_csv(dataset_path)
        df = df[['title', 'typename','typeid', 'tag', 'play', 'favorites']]
        
        # 处理 tag 列 - 更健壮的方法
        def parse_tags(tag_str):
            if pd.isna(tag_str):
                return []
            if isinstance(tag_str, list):
                return tag_str
            try:
                # 尝试使用 ast.literal_eval
                return ast.literal_eval(tag_str)
            except (ValueError, SyntaxError):
                try:
                    # 尝试使用 json.loads
                    return json.loads(tag_str)
                except (ValueError, SyntaxError):
                    try:
                        # 尝试使用 json.loads 并替换单引号为双引号
                        return json.loads(tag_str.replace("'", '"'))
                    except (ValueError, SyntaxError):
                        # 如果所有方法都失败，尝试简单的分割
                        # 移除方括号和引号，然后按逗号分割
                        cleaned = re.sub(r'[\[\]\'"\s]', '', tag_str)
                        return [tag for tag in cleaned.split(',') if tag]
        
        df['tag'] = df['tag'].apply(parse_tags)
        
        # 展开 tag 列表，使每个 tag 成为单独的行
        tag_exploded = df.explode('tag')
        
        # 移除可能为空的 tag
        tag_exploded = tag_exploded[tag_exploded['tag'].notna() & (tag_exploded['tag'] != '')]
        
        # 计算每个 tag 的加权出现次数（play 作为权重）
        play_weighted_tags = tag_exploded.groupby('tag')['play'].sum().reset_index(name='play_weighted')
        
        # 计算每个 tag 的加权出现次数（favorites 作为权重）
        favorites_weighted_tags = tag_exploded.groupby('tag')['favorites'].sum().reset_index(name='favorites_weighted')
        
        # 合并两个加权值
        merged_tags = pd.merge(play_weighted_tags, favorites_weighted_tags, on='tag', how='outer').fillna(0)
        
        # 归一化处理
        scaler = MinMaxScaler()
        try:
            merged_tags[['play_norm', 'favorites_norm']] = scaler.fit_transform(merged_tags[['play_weighted', 'favorites_weighted']])
        except ValueError:
            # 如果归一化失败（例如所有值相同），使用原始值
            merged_tags['play_norm'] = merged_tags['play_weighted']
            merged_tags['favorites_norm'] = merged_tags['favorites_weighted']
        
        # 计算综合得分（例如取平均值）
        merged_tags['score'] = (merged_tags['play_norm'] + merged_tags['favorites_norm']) / 2
        
        # 按得分排序，选择前10个 tag
        top10_tags = merged_tags.sort_values('score', ascending=False).head(10)
        
        # 计算每个 typename 的加权出现次数（play 作为权重）
        play_weighted = df.groupby('typename')['play'].sum().reset_index(name='play_weighted')
        
        # 计算每个 typename 的加权出现次数（favorites 作为权重）
        favorites_weighted = df.groupby('typename')['favorites'].sum().reset_index(name='favorites_weighted')
        
        # 合并两个加权值
        merged = pd.merge(play_weighted, favorites_weighted, on='typename', how='outer').fillna(0)
        
        # 归一化处理
        try:
            merged[['play_norm', 'favorites_norm']] = scaler.fit_transform(merged[['play_weighted', 'favorites_weighted']])
        except ValueError:
            # 如果归一化失败（例如所有值相同），使用原始值
            merged['play_norm'] = merged['play_weighted']
            merged['favorites_norm'] = merged['favorites_weighted']
        
        # 计算综合得分（例如取平均值）
        merged['score'] = (merged['play_norm'] + merged['favorites_norm']) / 2
        
        # 按得分排序
        merged_sorted = merged.sort_values('score', ascending=False)
        
        # 选择最佳 typename
        best_typename = merged_sorted.iloc[0]['typename'] if len(merged_sorted) > 0 else "Unknown"

        # 根据best_typename获取对应的typeid
        typeid = df[df['typename'] == best_typename]['typeid'].tolist()[0]
        
        # 返回结果
        return {
            'typename': best_typename,
            'typeid': typeid,
            'tags': top10_tags['tag'].tolist(),
            'description': '该视频由程序自动生成，QWQ'
        }
    except Exception as e:
        logger.error(f"处理文件 {dataset_path} 时出错: {e}")
        return {
            'dataset': os.path.basename(dataset_path),
            'error': str(e)
        }

async def main():
    # 获取所有日期文件夹
    dates = os.listdir(dataset_dir)
    if not dates:
        logger.error("没有找到任何日期文件夹")
        return
    
    # 获取最新日期的文件夹
    latest_date = sorted(dates)[-1]
    date_path = os.path.join(dataset_dir, latest_date)
    
    try:
        os.makedirs(source_dir, exist_ok=True)
    except: pass

    try:
        os.makedirs(f'{source_dir}/{latest_date}', exist_ok=True)
    except: pass

    # 获取该日期下的所有数据集文件
    datasets = [f for f in os.listdir(date_path) if f.endswith('.csv')]
    if not datasets:
        logger.error(f"在 {date_path} 中没有找到CSV文件")
        return
    
    # 创建所有数据集文件的完整路径
    dataset_paths = [os.path.join(date_path, dataset) for dataset in datasets]
    
    # 使用asyncio.gather同时处理所有文件
    tasks = [process_dataset(path) for path in dataset_paths]
    results = await asyncio.gather(*tasks)
    
    # 保存结果到JSON文件
    output_file = f'{source_dir}/{latest_date}/tags.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"处理完成，结果已保存到 {output_file}")

if __name__ == '__main__':
    print('开始分析今日热点')
    print('='*50)
    asyncio.run(main())
    print('='*50)
