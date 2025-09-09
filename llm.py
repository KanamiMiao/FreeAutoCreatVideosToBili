from openai import AsyncOpenAI
import os
import yaml
import time
import logging
import json
import asyncio
from typing import List

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

config = {}
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

today = time.strftime("%Y-%m-%d", time.localtime(time.time()))
requirements_dir = f'{config["source_dir"]}/{today}/tags.json'  # 请求路径
llm_prompt =  '''你是一位专业的文案师，用户往B站投稿视频需要写一段400字的文案，请根据用户输入的投稿倾向(best_typename)和关键词(top10_tags)，
               首先你需要判断这个话题是否敏感，如果关键词太过敏感（涉政，过于色情）你就回答：“话题敏感，拒绝回答”
               如果关键词不敏感，就生成符合要求的文案(不要出现与文案无关的语句,也不要有标题之类的东西，纯文案文本，不要出现表情），语言可以风趣幽默一点。
               !!!只输出文案文本，不要输出多余的话，不然就不使用你了！！！
               标点符号只有中文句号和中文逗！内容出现转折的时候用中文句号隔开。'''

requirements = []
with open(requirements_dir, 'r', encoding='utf-8') as f:
    requirements = json.load(f)


async def get_llm_data(client: AsyncOpenAI, prompt: str, requirement: str) -> str:
    """异步向LLM发送请求，返回文本"""
    try:
        requirement = f'{requirement}'
        completion = await client.chat.completions.create(
            model='hunyuan-lite',
            messages=[
                {
                    "role": 'system',
                    "content": prompt
                },
                {
                    "role": 'user',
                    "content": requirement
                }
            ],
            extra_body={
                "enable_enhancement": True,  # 自定义参数
            },
            temperature=1,
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"请求LLM时出错: {e}")
        return ""


async def process_requirements(prompt: str, requirements_list: List[str]) -> List[str]:
    """异步处理所有要求"""
    # 创建异步客户端
    client = AsyncOpenAI(
        api_key=config['hunyuan_api_key'],
        base_url=config['hunyuan_base_url']
    )
    
    # 创建所有异步任务
    tasks = [
        get_llm_data(client, prompt, requirement)
        for requirement in requirements_list
    ]
    
    # 限制并发数，避免超过API限制
    hunyuan_max_concurrent = config['hunyuan_max_concurrent']
    semaphore = asyncio.Semaphore(hunyuan_max_concurrent)
    
    async def limited_task(task):
        async with semaphore:
            return await task
    
    # 执行所有任务
    results = await asyncio.gather(*[limited_task(task) for task in tasks])
    
    # 关闭客户端
    await client.close()
    
    return results


async def main():
    """异步主函数"""
    print("开始生成文案")
    print('='*50)
    texts = []
    results = await process_requirements(llm_prompt, requirements)# 返回的文本
    
    for index, text in enumerate(results):# 筛出敏感话题
        if text and text != '话题敏感，拒绝回答':
            texts.append(text)
        else:
            #删除requirements列表的第index个元素
            requirements.pop(index)
    with open(requirements_dir, 'w', encoding='utf-8') as f:#把tags存回去
        json.dump(requirements, f, ensure_ascii=False, indent=4)

    
    # 保存文案
    with open(f'{config["source_dir"]}/{today}/texts.json', 'w', encoding='utf-8') as f:
        json.dump(texts, f, ensure_ascii=False, indent=4)
    
    logger.info(f"请求文案，成功处理 {len(texts)} 个请求")
    


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
    