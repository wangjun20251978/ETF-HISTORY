# ETF-HISTORY · ETF三因子轮动历史回看

任选日期区间，回看过去每个交易日的完整三因子数据。与 [ETF-ROTATION-PRO](https://github.com/wangjun20251978/ETF-ROTATION-PRO) 完全同口径（M动量40% + V相对低位30% + F资金流30% + 三重风控），红涨绿跌。

**在线看板**：https://wangjun20251978.github.io/ETF-HISTORY/

## 功能

- 📅 **日期区间自由选择**：起始/结束日期 + 快捷区间（近5/10/20/60日/全部），一键重新生成页面
- 📋 **每日概览**：大盘状态、建议仓位、当日推荐（前2且过风控）、通过数、上证涨跌
- 🔍 **单日明细**：点任意一天展开 48 只 ETF 完整因子（价格/日涨跌/5日/10日/M/V分位/V得分/F比值/F得分/综合/风控）
- 🏆 **区间排行**：按区间平均总分排序，进推荐次数、进前5次数、过风控天数、最好名次
- 🔁 **推荐切换轨迹**：只看推荐组合变化的关键时刻
- 📈 **走势图**：区间内每日风控通过数 + 大盘状态色带
- ⬇ **导出本区间**：生成独立单文件 HTML，双击即看
- 🔗 **URL 直达**：`?start=2026-09-01&end=2026-11-10&tab=rank`

## 自动更新

GitHub Actions 每交易日 **4 次**归档（北京时间 08:35 盘前 / 11:35 午间 / 15:35 收盘后 / 20:35 晚间）。

首次运行已回填约 **140 个交易日**（约 7 个月），之后每日追加。

## 本地使用

双击 `run.bat`：更新数据 → 自动打开页面（本地 bundle 模式，无需联网看历史）。

或命令行：`python etf_history.py`

## 数据结构

```
docs/data/index.json        索引（可用日期 + 每日概览，约21KB）
docs/data/YYYY-MM-DD.json   单日快照（48只全部因子，约8KB/天）
docs/data/local-bundle.js   本地双击兜底包（gitignore，不上传）
```

## 相关项目

| 项目 | 说明 |
|---|---|
| [ETF-ROTATION-PRO](https://github.com/wangjun20251978/ETF-ROTATION-PRO) | 三因子轮动看板 Pro（当日实盘） |
| [ETF-DASHBOARD2006](https://github.com/wangjun20251978/ETF-DASHBOARD2006) | 综合看板 |
| [ETF-FACTOR-SCORE](https://github.com/wangjun20251978/ETF-FACTOR-SCORE) | 个股多因子打分 |

> 历史数据不可改写，仅供复盘参考，不构成投资建议。
