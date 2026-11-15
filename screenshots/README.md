# 截图说明

本目录用于存放 README、作品集页面或面试展示材料中使用的截图。只提交经过脱敏、可公开展示且与本项目真实产物一致的图片，不伪造截图，也不引用不存在的路径。

## 当前已有截图

| 文件 | 说明 | 来源 |
| --- | --- | --- |
| `screenshots/dashboard_overview.png` | 自动生成的 Excel 看板 `00_看板` 页，展示 8 个 KPI 和 4 张图 | 由 `dashboard/auto_dashboard.xlsx` 导出 |
| `dashboard/dashboard_preview.png` | 早期手工版看板预览，保留作为对照 | 早期版本 |

README 另外引用了 `reports/figures/` 下由脚本生成的图表：

| 文件 | 说明 |
| --- | --- |
| `reports/figures/behavior_distribution.png` | 四种行为类型分布 |
| `reports/figures/daily_trends.png` | DAU 与每日购买趋势 |
| `reports/figures/hourly_behavior_heatmap.png` | 24 小时行为热力图 |
| `reports/figures/top_categories_purchase.png` | 购买次数 Top 品类 |
| `reports/figures/cohort_activity.png` | 首购 Cohort 活跃留存热力图 |
| `reports/figures/cohort_purchase.png` | 首购 Cohort 购买留存热力图 |

## 可选补充截图

| 建议文件名 | 说明 | 状态 |
| --- | --- | --- |
| `dify_knowledge_files.png` | Dify 知识库文档列表 | 本轮未做 Dify 升级，不引用 |
| `dify_qa_demo.png` | Dify 带引用的问答效果 | 本轮未做 Dify 升级，不引用 |
| `sql_query_example.png` | SQL 查询示例（CTE / 窗口函数） | 可选 |

## 使用建议

- README 顶部优先使用 `screenshots/dashboard_overview.png`，它对应脚本生成的真实看板。
- 只有图片真实存在时才写进 README；`screenshots/README.md` 中登记为“可选”的文件不要在 README 引用。
- 不提交完整原始数据截图，不展示 `data/UserBehavior.csv` 的内容。
- 截图要清晰、不要截到任务栏或无关窗口；更新看板后，记得重新导出并覆盖 `dashboard_overview.png`。

## 重新生成看板截图

1. 重新生成看板：

   ```powershell
   python src/generate_reports.py
   ```

2. 用 Excel / WPS 打开 `dashboard/auto_dashboard.xlsx`，切到 `00_看板` 页。
3. 调整窗口到合适大小，只截取看板区域，保存为 `screenshots/dashboard_overview.png`。
4. 确认 README 中引用的路径仍然是 `screenshots/dashboard_overview.png`。
