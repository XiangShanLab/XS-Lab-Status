# SCORING_RULES

## 1. 基础公式

- `base_score = complexity × 10`
- `stake = complexity × 10`
- `on_time_reward = base_score × 1.0`
- `late_reward = base_score × 0.6`
- `reviewer_reward = base_score × 0.1`

## 2. 质量系数

3 名 Reviewer 的平均分映射为质量系数，范围为 `0.5 ~ 1.2`。

建议映射：

- `1.0-1.9 -> 0.5`
- `2.0-2.4 -> 0.8`
- `2.5-3.4 -> 1.0`
- `3.5-4.4 -> 1.1`
- `4.5-5.0 -> 1.2`

## 3. 结果结算

### 3.1 按时完成

执行人获得：`base_score × quality_factor`。

### 3.2 延期完成

执行人获得：`base_score × 0.6 × quality_factor`。

若申请延期，则追加 20% 质押。

### 3.3 未完成

执行人扣除全部质押积分。

### 3.4 Review 奖励

每名 Reviewer 获得：`base_score × 0.1`。

## 4. 记录要求

所有结算结果必须写入 `ledger/score-log.md`，并保留可追溯的 Issue 编号、参与者、理由和计算结果。
