# GitHub Actions Workflow 说明

## 为什么Actions没有显示？

### 可能的原因：

1. **文件路径不正确**
   - 确保文件路径为：`.github/workflows/news-scraper.yml`
   - 文件名必须以 `.yml` 或 `.yaml` 结尾

2. **文件不在正确的分支**
   - workflow文件必须在 `main` 或 `master` 分支才能显示
   - 如果文件在其他分支，需要合并到主分支

3. **GitHub Actions被禁用**
   - 检查仓库设置：Settings → Actions → General
   - 确保 "Allow all actions and reusable workflows" 已启用

4. **workflow_dispatch需要手动触发**
   - 当前配置为 `workflow_dispatch`，不会自动运行
   - 需要手动在Actions页面点击 "Run workflow" 按钮

5. **YAML语法错误**
   - 检查YAML格式是否正确
   - 确保缩进使用空格而不是Tab

## 如何查看和使用：

1. **查看workflow**
   - 进入仓库的 Actions 标签页
   - 应该能看到 "新闻采集工具" workflow

2. **手动触发**
   - 点击 "新闻采集工具" workflow
   - 点击右侧 "Run workflow" 按钮
   - 输入搜索关键字和平台
   - 点击 "Run workflow" 执行

3. **自动触发（已添加）**
   - 当推送代码到 main/master 分支时
   - 如果修改了 workflow 文件或 scraper.py
   - 会自动运行（使用默认参数）

## 故障排查：

如果Actions仍然不显示：

1. 检查文件是否已提交：
   ```bash
   git status
   git add .github/workflows/news-scraper.yml
   git commit -m "Add workflow"
   git push
   ```

2. 检查文件内容是否正确：
   ```bash
   cat .github/workflows/news-scraper.yml
   ```

3. 检查GitHub仓库设置中的Actions权限

4. 等待几分钟，GitHub可能需要时间同步
