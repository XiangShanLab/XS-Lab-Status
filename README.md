# XS-Lab-Status

去中心化任务管理与积分榜仓库。

## 当前目标

- 通过 GitHub Issue 管理任务生命周期
- 通过 `ledger/score-log.md` 记录所有积分变更
- 通过 README 展示积分榜
- 通过标准化模板支持任务、交付、审查和周报

## P0 交付物

- `docs/PROCESS.md`
- `docs/SCORING_RULES.md`
- `ledger/task.schema.json`
- `ledger/delivery.schema.json`
- `ledger/review.schema.json`
- `.github/ISSUE_TEMPLATE/`
- `scripts/issue_automation.py`
- `scripts/validate_metadata.py`
- `scripts/generate_leaderboard.py`
- `ledger/score-log.md`

## 目录

- `.github/ISSUE_TEMPLATE/`：任务、交付、Review 模板
- `.github/workflows/`：Issue 校验和命令入口
- `docs/`：流程与积分规则
- `ledger/`：积分账本与 Schema
- `scripts/`：解析、校验与积分生成脚本
- `weekly-reports/`：周报模板

## 约定命令

- `/assign`
- `/ready-for-review`
- `/extend`

## 记录原则

所有关键操作都应落到 Issue、评论或 `ledger/`，仓库历史作为审计依据。
