import requests
import os
import yaml
import logging
import json
import asyncio

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

config = {}
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

pexels_api_key = config['pexels_api_key']
pexels_base_url = config['pexels_base_url']



# 请求头，包含认证信息
headers = {
    'Authorization': pexels_api_key
}

# 查询参数
params = {
    'query': 'nature',  # 搜索关键词
    'per_page': 15,     # 每页结果数量（可选，默认15，最大80）
    'page': 1           # 页码（可选，默认1）
}

# 发送 GET 请求
response = requests.get(pexels_base_url, headers=headers, params=params)

# 检查请求是否成功
if response.status_code == 200:
    data = response.json()
    print("请求成功！")
    print(f"找到 {data['total_results']} 个结果。")
    # 处理视频数据...
else:
    print(f"请求失败，状态码：{response.status_code}")
    print(response.text)