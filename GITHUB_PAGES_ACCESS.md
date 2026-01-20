# GitHub Pages 访问指南

## 📍 访问地址格式

根据您的仓库信息，GitHub Pages 的访问地址为：

```
https://{username}.github.io/{repository-name}/
```

### 实际示例

假设您的仓库信息是：
- **用户名/组织名**: `fmzh2021`
- **仓库名**: `news-collection`

那么访问地址为：
- **主页**: `https://fmzh2021.github.io/news-collection/`
- **最新结果 JSON**: `https://fmzh2021.github.io/news-collection/results_latest.json`
- **历史结果 JSON**: `https://fmzh2021.github.io/news-collection/results_xxx.json`

**注意**：由于 workflow 配置了 `publish_dir: ./api`，`api/` 目录的内容会被部署到 gh-pages 分支的根目录，所以访问路径**不需要** `api/` 前缀。

## 🔧 启用 GitHub Pages

如果还没有启用 GitHub Pages，请按以下步骤操作：

### 方法1：通过 GitHub Actions 自动部署（推荐）

您的 workflow 已经配置了自动部署，只需要：

1. **确保 workflow 已运行**
   - 进入仓库的 **Actions** 标签页
   - 确认 workflow 已成功执行
   - 查看是否有 "部署到GitHub Pages" 步骤成功

2. **启用 GitHub Pages**
   - 进入仓库 **Settings** → **Pages**
   - 在 **Source** 部分，选择：
     - **Source**: `Deploy from a branch`
     - **Branch**: `gh-pages`（workflow 会自动创建）
     - **Folder**: `/ (root)`
   - 点击 **Save**

3. **等待部署完成**
   - GitHub Pages 通常需要几分钟才能生效
   - 部署完成后，您会看到绿色的成功提示

### 方法2：手动检查 gh-pages 分支

```bash
# 查看远程分支
git fetch origin
git branch -r | grep gh-pages

# 如果存在 gh-pages 分支，说明部署成功
```

## 📂 文件访问路径

根据您的 workflow 配置，`publish_dir: ./api`，所以文件结构如下：

```
gh-pages 分支根目录/
├── index.html          # API 主页
├── results_latest.json # 最新结果
└── results_*.json      # 历史结果文件
```

### 访问路径示例

| 文件 | 访问 URL |
|------|----------|
| API 主页 | `https://fmzh2021.github.io/news-collection/` |
| 最新结果 | `https://fmzh2021.github.io/news-collection/results_latest.json` |
| 历史结果 | `https://fmzh2021.github.io/news-collection/results_xxx.json` |

**说明**：workflow 配置了 `publish_dir: ./api`，这意味着 `api/` 目录的内容会被部署到 gh-pages 分支的**根目录**，所以访问路径**直接使用根路径**即可，不需要 `api/` 前缀。

## 🔍 检查部署状态

### 1. 检查 Actions 运行状态

```bash
# 在 GitHub 网页上
1. 进入仓库的 Actions 标签页
2. 查看最新的 workflow 运行
3. 确认 "部署到GitHub Pages" 步骤显示 ✅
```

### 2. 检查 gh-pages 分支

```bash
# 在本地执行
git fetch origin gh-pages
git checkout gh-pages
ls -la  # 查看文件列表
```

### 3. 检查 Pages 设置

1. 进入 **Settings** → **Pages**
2. 查看 **Custom domain**（如果有）
3. 查看部署状态和最后更新时间

## 🌐 访问方式

### 方式1：浏览器访问

直接在浏览器中打开：
```
https://fmzh2021.github.io/news-collection/
```

### 方式2：使用 curl

```bash
# 获取最新结果
curl https://fmzh2021.github.io/news-collection/results_latest.json

# 获取 API 主页
curl https://fmzh2021.github.io/news-collection/
```

### 方式3：使用 Python

```python
import requests

# 获取最新结果
url = "https://fmzh2021.github.io/news-collection/results_latest.json"
response = requests.get(url)
data = response.json()
print(data)
```

### 方式4：使用 JavaScript

```javascript
// 获取最新结果
fetch('https://fmzh2021.github.io/news-collection/results_latest.json')
  .then(res => res.json())
  .then(data => console.log(data));
```

## ⚠️ 常见问题

### 1. 404 错误

**原因**：
- GitHub Pages 还未启用
- gh-pages 分支不存在
- 文件路径不正确

**解决方法**：
1. 检查 Settings → Pages 是否已启用
2. 确认 workflow 已成功运行
3. 检查文件路径是否正确（注意 `api/` 前缀）

### 2. 页面显示旧内容

**原因**：
- GitHub Pages 缓存
- 部署还未完成

**解决方法**：
1. 等待几分钟后刷新（Ctrl+F5 强制刷新）
2. 检查 Actions 中最新部署是否成功

### 3. 找不到 gh-pages 分支

**原因**：
- workflow 还未运行
- workflow 执行失败

**解决方法**：
1. 手动触发 workflow 运行
2. 检查 workflow 日志中的错误信息

## 🔗 相关链接

- [GitHub Pages 文档](https://docs.github.com/zh/pages)
- [peaceiris/actions-gh-pages](https://github.com/peaceiris/actions-gh-pages)
- [查看您的 Pages 设置](https://github.com/fmzh2021/news-collection/settings/pages)

## 📝 快速检查清单

- [ ] workflow 已成功运行
- [ ] Settings → Pages 已启用
- [ ] gh-pages 分支已创建
- [ ] 可以访问 `https://fmzh2021.github.io/news-collection/`
- [ ] 可以访问 `https://fmzh2021.github.io/news-collection/results_latest.json`
