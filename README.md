# 新闻采集和总结工具

一个基于 GitHub Actions 的新闻采集工具，支持从头条、Google、Bing 三个平台搜索新闻并返回 JSON 格式结果。

## 功能特性

- 🔍 支持关键字搜索
- 📰 支持头条、Google、Bing 三个平台
- 📄 返回标题和 URL 的 JSON 格式数据
- ⚡ 通过 GitHub Actions 手动触发执行
- 🎯 每个平台最多返回 10 条结果

## 使用方法

### 通过 GitHub Actions 使用

1. 进入项目的 Actions 页面
2. 选择 "新闻采集工具" workflow
3. 点击 "Run workflow" 按钮
4. 输入搜索关键字
5. 选择要搜索的平台（可选，默认为所有平台）
6. 点击 "Run workflow" 执行

执行完成后，结果会保存在 `results.json` 文件中，并作为 Artifact 下载。

### 本地使用

```bash
# 安装依赖
pip install -r requirements.txt

# 运行脚本
python scraper.py "搜索关键字" "toutiao,google,bing"
```

## 输出格式

```json
{
  "keyword": "搜索关键字",
  "total": 30,
  "platforms": ["toutiao", "google", "bing"],
  "results": [
    {
      "title": "新闻标题",
      "url": "https://example.com/news",
      "platform": "toutiao"
    }
  ]
}
```

## 项目结构

```
news-json-api/
├── .github/
│   └── workflows/
│       └── news-scraper.yml    # GitHub Actions 工作流
├── scraper.py                   # 主爬虫脚本
├── requirements.txt             # Python 依赖
└── README.md                    # 项目说明
```

## 问题解决

### 1. 头条数据获取问题
头条网站有较强的反爬虫机制，已优化解析逻辑：
- 改进了JSON数据提取方法
- 增加了多种HTML选择器策略
- 添加了API接口尝试（可能受签名限制）
- 如果仍然无法获取，建议使用Playwright等浏览器自动化工具

### 2. 并发覆盖问题
已解决并发执行时的文件覆盖问题：
- 使用唯一文件名：`results_{run_id}_{run_number}_{timestamp}.json`
- 每个运行都有独立的Artifact
- 同时保留 `results_latest.json` 作为最新结果

### 3. 外部获取数据
提供三种方式获取结果：

**方式1: GitHub Pages API**
```bash
# 获取最新结果
curl https://{username}.github.io/{repo}/api/results_latest.json
```

**方式2: GitHub Artifacts**
- 在GitHub Actions运行完成后，在Artifacts中下载 `news-results-{run_id}`

**方式3: GitHub API**
```bash
# 获取所有Artifacts列表
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/{owner}/{repo}/actions/artifacts

# 下载特定Artifact
curl -L -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/{owner}/{repo}/actions/artifacts/{artifact_id}/zip
```

## 注意事项

- 搜索结果依赖于各平台的 HTML 结构，如果平台更新页面结构可能需要调整解析逻辑
- 某些平台可能有反爬虫机制，建议合理使用频率
- 结果数量可能因平台和关键字而异
- 头条数据可能需要浏览器渲染，如持续无法获取建议使用Playwright

## 许可证

MIT License
