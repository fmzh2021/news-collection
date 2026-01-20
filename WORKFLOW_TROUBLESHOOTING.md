# GitHub Actions Workflow 显示问题排查指南

## 问题：Workflow 不显示名称和 "Run workflow" 按钮

### ✅ 已确认配置正确
- ✅ `name: 新闻采集工具` - 已设置
- ✅ `workflow_dispatch:` - 已配置手动触发
- ✅ YAML 语法正确

### 🔍 排查步骤

#### 1. 确认文件位置和分支
```bash
# 检查文件是否存在
ls -la .github/workflows/news-scraper.yml

# 确认当前分支
git branch

# 确认是否在默认分支（master/main）
git remote show origin | grep "HEAD branch"
```

**重要**：workflow 文件必须在**默认分支**上才能显示 "Run workflow" 按钮。

#### 2. 检查仓库 Actions 设置
1. 进入仓库 Settings → Actions → General
2. 确认 "Allow all actions and reusable workflows" 已启用
3. 确认 "Workflow permissions" 设置为 "Read and write permissions"

#### 3. 验证 YAML 语法
访问：https://www.yamllint.com/ 或使用 GitHub 的验证

#### 4. 检查 Actions 页面
1. 进入仓库的 **Actions** 标签页
2. 查看左侧是否有 "新闻采集工具" workflow
3. 如果没有，点击 "All workflows" 查看所有 workflow

#### 5. 等待 GitHub 识别
- 新添加的 workflow 可能需要几分钟才能显示
- 尝试刷新页面（Ctrl+F5 或 Cmd+Shift+R）

#### 6. 检查是否有错误提示
- 在 Actions 页面查看是否有红色错误提示
- 查看 "Workflow definitions" 是否有语法错误

### 🛠️ 解决方案

#### 方案1：确保文件在默认分支
```bash
# 如果当前不在默认分支，切换到默认分支
git checkout master  # 或 main

# 确保 workflow 文件存在
git add .github/workflows/news-scraper.yml
git commit -m "Add workflow file"
git push origin master
```

#### 方案2：重新创建 workflow 文件
如果文件存在但 GitHub 不识别，可以：
1. 删除 `.github/workflows/news-scraper.yml`
2. 重新创建并提交
3. 等待几分钟后刷新 Actions 页面

#### 方案3：简化 workflow 测试
创建一个最简单的测试 workflow 来验证：

```yaml
name: Test Workflow

on:
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Test
        run: echo "Workflow is working!"
```

### 📋 常见问题

#### Q: 免费账号会影响显示吗？
**A:** 不会。免费账号限制的是运行时间（私有仓库每月 2000 分钟），不影响 workflow 的显示和功能。

#### Q: master 分支名会影响吗？
**A:** 不会。只要它是默认分支就可以。GitHub 现在默认使用 `main`，但 `master` 同样有效。

#### Q: 为什么看不到 "Run workflow" 按钮？
**A:** 可能的原因：
1. workflow 文件不在默认分支上
2. 仓库禁用了 Actions
3. 文件路径不正确（必须是 `.github/workflows/*.yml`）
4. YAML 语法错误导致 GitHub 无法解析

### 🔗 相关链接
- [GitHub Actions 文档](https://docs.github.com/zh/actions)
- [手动运行工作流](https://docs.github.com/zh/actions/managing-workflow-runs/manually-running-a-workflow)
- [工作流语法](https://docs.github.com/zh/actions/using-workflows/workflow-syntax-for-github-actions)
