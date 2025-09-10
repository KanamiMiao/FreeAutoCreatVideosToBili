# 全自动造史器

[AI分析](https://deepwiki.com/KanamiMiao/FreeAutoCreatVideosToBili)

## 功能
1. 获取b站信息：使用 GitHub 上的项目 [bilibili-api](https://github.com/Nemo2011/bilibili-api)
2. 大语言模型：使用腾讯 [混元大模型](https://console.cloud.tencent.com/hunyuan/start)
3. 文本转语音：使用 GitHub 上的项目 [edge-tts](https://github.com/rany2/edge-tts)
4. 视频片段资源：使用 [Pexels API](https://www.pexels.com/api/documentation/)

## 使用方法

1. 下载项目到本地
2. 修改 config.json 中的配置
3. 双击 setup.bat 自动安装依赖
4. 双击 run.bat 自动运行程序
5. 视频会保存在 `sources\日期\videos_out` 目录下

## 注意事项

1. 本项目实际效果未达预期
2. 本程序使用腾讯混元大模型，需要申请腾讯云账号并开通相关服务
3. 本程序使用 Pexels API，需要申请 Pexels 账号并开通相关服务