# vEuropean Release Notes

记录 vEuropean 源数据 / 生成报告 / 公开产物的每次变更。每次执行 `npm run generate:data:europe` 后追加一节，记录政权数、年度行数、事件数与已知问题。

## 未发布 — 骨架版

- 创建 `input/vEuropean/` 目录与 manifest。
- 复制 `input/templates/` 模板为占位 CSV（仅表头，无数据行）。
- 创建 `admin_boundaries/` 子目录，等待 `prepare_european_admin_boundaries.py` 首次拉取。
- 已知缺：所有政权 / 君主 / 事件 / 首都 / 战略位点尚未写入；将在 `bootstrap_european_dataset.py` 中按 8 个时代段批量录入。
