# GitHub 发布清单

## 发布前

- [ ] 确认仓库中没有 `.env`、API Key、个人简历、电话、邮箱或真实企业数据。
- [ ] 确认所有设备、门店、告警、工单和知识资料都标注为模拟数据。
- [ ] 本地执行 `python -m pytest -q`。
- [ ] 本地执行 `python evals/run_eval.py`，确认 `failed_case_ids` 为空。
- [ ] 本地启动 `python -m uvicorn app.main:app --reload`，完成 README 中的五分钟演示。
- [ ] 检查 `docs/images/demo-dashboard.png` 可以正常展示。

## 创建远程仓库

在 GitHub 网页端创建一个空仓库，例如：

```text
ai-device-after-sales-copilot
```

不要勾选自动创建 README、`.gitignore` 或 License，因为本地项目已经包含这些文件。

## 首次推送

```powershell
git branch -M main
git add .
git commit -m "feat: add AI device after-sales copilot MVP"
git remote add origin <你的 GitHub 仓库地址>
git push -u origin main
```

其中 `<你的 GitHub 仓库地址>` 需要替换为你自己创建的仓库地址。不要把 Token、密码或个人敏感信息写进命令、代码或 README。

## 投递使用

- README 首页：展示截图、产品定位和五分钟演示路径。
- `docs/portfolio/project-experience.md`：复制到简历和面试准备材料。
- `docs/portfolio/evaluation-summary.md`：面试时说明如何验证 AI 输出质量。
- GitHub Actions：展示每次 push 和 Pull Request 都会自动运行测试和评测。
