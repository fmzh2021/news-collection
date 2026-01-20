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
   - 如果看不到，检查文件路径：`.github/workflows/news-scraper.yml`

2. **手动触发（唯一方式）**
   - 点击左侧的 "新闻采集工具" workflow
   - 点击右侧绿色的 "Run workflow" 下拉按钮
   - 选择分支（通常是 main 或 master）
   - 输入搜索关键字（必填）
   - 选择平台（可选，默认所有平台）
   - 点击 "Run workflow" 按钮执行

3. **重要说明**
   - ⚠️ 当前配置为**仅手动触发**，不会自动运行
   - ✅ 这样可以避免push时循环构建
   - ✅ 提交JSON文件不会触发新的workflow

## 故障排查：

### 如果看不到 "Run workflow" 按钮：

1. **确认文件已提交到GitHub**
   ```bash
   git status
   git add .github/workflows/news-scraper.yml
   git commit -m "Add workflow"
   git push origin main  # 或 master
   ```

2. **确认文件在主分支**
   - workflow文件必须在 `main` 或 `master` 分支
   - 如果文件在其他分支，需要合并到主分支

3. **检查GitHub Actions是否启用**
   - 进入仓库 Settings → Actions → General
   - 确保 "Allow all actions and reusable workflows" 已启用
   - 确保 "Workflow permissions" 设置为 "Read and write permissions"

4. **刷新页面**
   - 按 `Ctrl+F5` (Windows) 或 `Cmd+Shift+R` (Mac) 强制刷新
   - 或者等待几分钟让GitHub同步

5. **检查workflow文件位置**
   - 文件路径必须是：`.github/workflows/news-scraper.yml`
   - 文件名必须以 `.yml` 或 `.yaml` 结尾

6. **检查YAML语法**
   - 确保缩进使用空格（不是Tab）
   - 确保 `workflow_dispatch` 正确配置

### 如何找到 "Run workflow" 按钮：

1. 进入 GitHub 仓库页面
2. 点击顶部的 **Actions** 标签
3. 在左侧边栏点击 **news-scraper.yml** workflow
4. 在右侧应该能看到绿色的 **"Run workflow"** 按钮
5. 如果看不到，检查上面的故障排查步骤
