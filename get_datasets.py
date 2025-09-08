from bilibili_api import search,sync
import time
import asyncio
import os
import yaml
import pandas as pd
import random
from typing import List, Dict, Any
import logging

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
keywords_num = config['keywords_num']
day_range = config['day_range']
base_sleep_time = config['base_sleep_time']  # 基础获取间隔时间
max_retries = config['max_retries']  # 最大重试次数
concurrent_keywords = config['concurrent_keywords']  # 并发处理的关键词数量


class Fetch_data:
    @staticmethod
    def get_day(i):  # 获取i天前的日期
        return time.strftime("%Y-%m-%d", time.localtime(time.time() - i * 24 * 60 * 60))

    async def get_day_data(self, keyword: str, now_page: int, date: list) -> pd.DataFrame:
        """获取单日数据"""
        day_data = pd.DataFrame()
        retries = 0
        
        while retries < max_retries:
            # 添加随机延迟，避免固定间隔请求
            sleep_time = base_sleep_time * (1 + random.random())  # 1-2倍基础延迟
            await asyncio.sleep(sleep_time)
            
            try:
                result = await search.search_by_type(
                    keyword=keyword,
                    search_type=search.SearchObjectType.VIDEO,
                    page=now_page,
                    time_start=date[0],
                    time_end=date[1]
                )
                
                page_data = pd.DataFrame(result['result'])
                if page_data.empty:
                    logger.debug(f"关键词 '{keyword}' 日期 {date[0]} 第 {now_page} 页无数据")
                    break
                    
                day_data = pd.concat([day_data, page_data], ignore_index=True)
                logger.debug(f"已获取关键词 '{keyword}' 日期 {date[0]} 第 {now_page} 页的数据，共 {len(page_data)} 条")
                now_page += 1
                    
            except Exception as e:
                if '网络错误，状态码：412' in str(e):
                    retries += 1
                    wait_time = sleep_time * (2 ** retries)  # 指数退避策略
                    logger.warning(f"关键词 '{keyword}' 日期 {date[0]} 请求被风控，第 {retries} 次重试，等待 {wait_time} 秒")
                    await asyncio.sleep(wait_time)
                else:
                    # logger.error(f"获取关键词 '{keyword}' 日期 {date[0]} 数据时发生错误: {e}")
                    break
        
        if not day_data.empty:
            logger.info(f"关键词 '{keyword}' 日期 {date[0]} 的数据获取完毕，共 {len(day_data)} 条数据")
        else:
            logger.warning(f"关键词 '{keyword}' 日期 {date[0]} 未获取到任何数据")
            
        return day_data

    async def get_all_data_for_keyword(self, keyword: str, day_range: int) -> pd.DataFrame:
        """为单个关键词获取所有数据"""
        logger.info(f"开始获取关键词 '{keyword}' 的数据")
        
        all_data = pd.DataFrame()
        for i in range(0, day_range):
            date = [self.get_day(i), self.get_day(i - 1)]  # 生成日期范围
            day_data = await self.get_day_data(keyword, 1, date)  # 从第一页开始
            
            if not day_data.empty:
                all_data = pd.concat([all_data, day_data], ignore_index=True)
                
                # 每天数据获取完成后添加额外延迟
                await asyncio.sleep(base_sleep_time * 0.5 * (1 + random.random()))
        
        # 保存数据
        if not all_data.empty:
            save_dir = f'{dataset_dir}/{self.get_day(0)}'
            os.makedirs(save_dir, exist_ok=True)
            all_data.to_csv(f'{save_dir}/{keyword}.csv', index=False, encoding='utf-8-sig')
            logger.info(f"关键词 '{keyword}' 的数据已保存，共 {len(all_data)} 条")
        else:
            logger.warning(f"关键词 '{keyword}' 未获取到任何数据")
            
        return all_data

    async def get_all_data_for_keywords(self, keywords: List[str], day_range: int) -> List[pd.DataFrame]:
        """使用信号量控制并发获取多个关键词的数据"""
        semaphore = asyncio.Semaphore(concurrent_keywords)
        
        async def limited_task(keyword):
            async with semaphore:
                return await self.get_all_data_for_keyword(keyword, day_range)
                
        tasks = [limited_task(keyword) for keyword in keywords]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理可能出现的异常
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"获取关键词 '{keywords[i]}' 的数据时发生错误: {result}")
                
        return [r for r in results if not isinstance(r, Exception)]


async def get_hot_keywords():
    """获取当前热搜关键词"""
    try:
        hot_keywords = sync(search.get_hot_search_keywords())
        df = pd.DataFrame(hot_keywords['list'])
        logger.info(f"成功获取 {len(df)} 个热搜关键词")
        return df['keyword'].tolist()
    except Exception as e:
        logger.error(f"获取热搜关键词失败: {e}")
        return []


async def main():
    fd = Fetch_data()
    
    # 获取热搜关键词
    keywords = await get_hot_keywords()
    if keywords_num == 10:
        pass
    else:
        keywords = keywords[:keywords_num]
        
    if not keywords:
        logger.error("未获取到任何关键词，程序退出")
        return
    
    logger.info(f"开始获取 {len(keywords)} 个关键词的数据，时间范围 {day_range} 天")
    
    start_time = time.time()
    
    # 创建存储目录
    os.makedirs(f'{dataset_dir}/{fd.get_day(0)}', exist_ok=True)
    
    # 并发获取所有关键词的数据
    await fd.get_all_data_for_keywords(keywords, day_range)
    
    end_time = time.time()
    duration = (end_time - start_time) / 60
    logger.info(f"获取完成，总共耗时 {duration:.2f} 分钟")
    
if __name__ == '__main__':
    print('开始获取今日热点与相关视频数据')
    print('='*50)
    asyncio.run(main())
    print('='*50)
