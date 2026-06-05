# 🛡️ 全天候策略看板

基于 LongPort API 的投资收益公开看板，展示桥水全天候配置组合（YMAG + DBMF + SPDW + IAUI + GUNR）。

## 功能

- 实时展示 5 只 ETF 持仓明细（份额、成本价、现价、盈亏）
- 总投资 / 当前价值 / 总盈亏 KPI
- 持仓比例可视化
- 自动每日更新（北京时间 8:00）

## 配置步骤

### 1. 创建 GitHub 仓库

在 GitHub 新建一个公开仓库（如 `allweather-dashboard`），把本项目所有文件推上去。

### 2. 配置 GitHub Secrets

在仓库 Settings → Secrets and variables → Actions 中添加：

| Secret 名称 | 值来源 |
|---|---|
| `LONGPORT_APP_KEY` | LongPort 开发者中心 → App Key |
| `LONGPORT_APP_SECRET` | LongPort 开发者中心 → App Secret |
| `LONGPORT_ACCESS_TOKEN` | LongPort 开发者中心 → Access Token |

### 3. 启用 GitHub Pages

仓库 Settings → Pages → Source 选择 **GitHub Actions**

### 4. 首次触发 Actions

在仓库 Actions 页面点击 "Fetch All-Weather Portfolio Data" → "Run workflow"，手动运行一次。

## 本地预览

直接用浏览器打开 `index.html` 即可（数据从 `data/latest.json` 读取）。

## 数据更新逻辑

```bash
GitHub Actions (每日 UTC 0:00)
  → Python 脚本调用 LongPort API
  → 获取持仓 + 实时行情
  → 保存 data/latest.json
  → GitHub Pages 读取展示
```
