#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF 历史回看 · 数据归档器
=========================================
与 ETF-ROTATION-PRO 完全同口径 (M动量40% + V相对低位30% + F资金流30% + 三重风控)

作用:
  抓 48 只 ETF 的日 K 线 -> 逐交易日重算三因子 -> 每个交易日存一份完整快照
  前端 docs/index.html 读取这些快照, 支持任意日期区间回看 / 重新生成页面

输出:
  docs/data/YYYY-MM-DD.json   单日完整快照 (48只 ETF 全部因子)
  docs/data/index.json        索引(可用日期 + 每日概览)

回填: 首次运行会自动回填过去约 100 个交易日 (受 K 线长度限制)
幂等: 历史日期的文件已存在则跳过, 只有最新交易日每次覆盖
本地: python etf_history.py   或双击 run.bat
"""
import json
import os
import sys
import datetime
import urllib.request

# ===================== 参数区 (与 ETF-ROTATION-PRO 一致) =====================
MOMENTUM_SHORT = 10
MOMENTUM_LONG = 20
V_PERIOD = 60
MA_PERIOD = 20
F_SHORT = 5
F_LONG = 20
STOP_LOSS = -5.0
W_M, W_V, W_F = 0.4, 0.3, 0.3

HOLD_SIGNAL = 2                 # 信号: 综合前2 且 风控通过
MARKET_INDEX = "sh000001"       # 上证综指
BULL_WEIGHT, NEUTRAL_WEIGHT, BEAR_WEIGHT = 100, 50, 20

KLINE_DAYS = 200                # 抓取K线长度 -> 可回填约 140 个交易日

ETFS = [
    ("sz159915", "创业板ETF"), ("sh510500", "中证500ETF"), ("sh518880", "黄金ETF"),
    ("sh512100", "中证1000ETF"), ("sh588000", "科创50ETF"), ("sh516160", "新能源ETF"),
    ("sh510300", "沪深300ETF"), ("sh512480", "半导体ETF"), ("sh512660", "军工ETF"),
    ("sz159766", "旅游ETF"), ("sh515050", "通信ETF"), ("sh513100", "纳指ETF"),
    ("sh512400", "有色金属ETF"), ("sh513500", "标普500ETF"), ("sz159928", "消费ETF"),
    ("sh513180", "恒生科技ETF"), ("sh512690", "酒ETF"), ("sh512800", "银行ETF"),
    ("sz159920", "恒生ETF"), ("sh512070", "证券保险ETF"), ("sh512010", "医药ETF"),
    ("sh510050", "上证50ETF"), ("sh563300", "中证2000ETF"), ("sz159901", "深证100ETF"),
    ("sz159601", "A50ETF"),
    ("sh515080", "中证红利ETF"), ("sh512890", "红利低波ETF"),
    ("sh515790", "光伏ETF"), ("sh515220", "煤炭ETF"), ("sh516150", "稀土ETF"),
    ("sh515210", "钢铁ETF"), ("sz159870", "化工ETF"), ("sz159825", "农业ETF"),
    ("sz159996", "家电ETF"), ("sz159745", "建材ETF"), ("sh516110", "汽车ETF"),
    ("sh516950", "基建ETF"), ("sz159611", "电力ETF"),
    ("sh515980", "人工智能ETF"), ("sh562500", "机器人ETF"), ("sh515230", "软件ETF"),
    ("sh512980", "传媒ETF"),
    ("sh513520", "日经ETF"), ("sh513030", "德国ETF"), ("sh513080", "法国ETF"),
    ("sz159985", "豆粕ETF"), ("sh511260", "十年国债ETF"), ("sh511090", "30年国债ETF"),
]

HEADERS = {
    "Referer": "https://finance.sina.com.cn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}

BASE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE, "docs")
DATA = os.path.join(DOCS, "data")


# ===================== 抓取 =====================
def fetch_kline(symbol, datalen=KLINE_DAYS, retry=3):
    url = ("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
           "CN_MarketData.getKLineData?symbol=%s&scale=240&ma=no&datalen=%d" % (symbol, datalen))
    last_err = None
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("gbk", "ignore")
            data = json.loads(raw)
            rows = [{"day": d["day"], "open": float(d["open"]), "high": float(d["high"]),
                     "low": float(d["low"]), "close": float(d["close"]),
                     "volume": float(d["volume"])} for d in data]
            rows.sort(key=lambda x: x["day"])
            return rows
        except Exception as e:
            last_err = e
    raise last_err


# ===================== 因子 (同口径) =====================
def compute_from(closes, vols):
    n = len(closes)
    if n < V_PERIOD + 1:
        return None
    cur, prev = closes[-1], closes[-2]
    p10 = closes[-1 - MOMENTUM_SHORT] if n > MOMENTUM_SHORT else closes[0]
    p20 = closes[-1 - MOMENTUM_LONG] if n > MOMENTUM_LONG else closes[0]
    r10 = (cur / p10 - 1) * 100
    r20 = (cur / p20 - 1) * 100
    m = r10 * 0.6 + r20 * 0.4
    p5 = closes[-1 - 5] if n > 5 else closes[0]
    r5 = (cur / p5 - 1) * 100

    win = closes[-V_PERIOD:]
    lo, hi = min(win), max(win)
    v_pct = (cur - lo) / (hi - lo) * 100 if hi > lo else 50.0
    v_score = 100 - v_pct

    if n >= F_LONG:
        f_ratio = (sum(vols[-F_SHORT:]) / F_SHORT) / (sum(vols[-F_LONG:]) / F_LONG)
    else:
        f_ratio = 1.0
    f_score = f_ratio * 50
    total = W_M * m + W_V * v_score + W_F * f_score

    ma_now = sum(closes[-MA_PERIOD:]) / MA_PERIOD
    ma_prev = sum(closes[-MA_PERIOD - 1:-1]) / MA_PERIOD
    p3 = closes[-4] if n >= 4 else closes[0]
    drop3 = (cur / p3 - 1) * 100
    passed = (cur > ma_now) and (ma_now > ma_prev) and (drop3 >= STOP_LOSS)

    return {
        "p": round(cur, 4), "dc": round((cur / prev - 1) * 100, 2),
        "t10": round(r10, 2), "t5": round(r5, 2),
        "m": round(m, 2), "vp": round(v_pct, 1), "vs": round(v_score, 1),
        "fr": round(f_ratio, 3), "fs": round(f_score, 1),
        "t": round(total, 2), "pass": bool(passed),
    }


def factor_map(rows):
    """{交易日: 因子}  从第 V_PERIOD 根K线起每天一份"""
    out = {}
    if not rows or len(rows) < V_PERIOD + 1:
        return out
    closes = [r["close"] for r in rows]
    vols = [r["volume"] for r in rows]
    for idx in range(V_PERIOD, len(rows)):
        f = compute_from(closes[:idx + 1], vols[:idx + 1])
        if f:
            out[rows[idx]["day"]] = f
    return out


def market_map(rows):
    """{交易日: 大盘状态} 与 fetch_market_trend 同判定"""
    out = {}
    closes = [r["close"] for r in rows]
    for idx in range(len(rows)):
        if idx < 59:
            continue
        c = closes[:idx + 1]
        cur = c[-1]
        ma20 = sum(c[-20:]) / 20.0
        ma60 = sum(c[-60:]) / 60.0
        mom20 = (cur / c[-21] - 1) * 100
        bull = ma20 > ma60
        above = cur > ma20
        score = (0.5 if bull else 0) + (0.3 if above else 0) + (0.2 if mom20 > 0 else 0)
        if score >= 0.7 and mom20 > 0:
            state, w = "强势", BULL_WEIGHT
        elif (not bull) and (not above) and mom20 < 0:
            state, w = "弱势", BEAR_WEIGHT
        else:
            state, w = "中性", NEUTRAL_WEIGHT
        out[rows[idx]["day"]] = {
            "st": state, "w": w, "close": round(cur, 2),
            "mom": round(mom20, 2),
        }
    return out


# ===================== 主流程 =====================
def main():
    os.makedirs(DATA, exist_ok=True)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    print("[1/4] 抓取大盘指数 %s ..." % MARKET_INDEX)
    try:
        mk_rows = fetch_kline(MARKET_INDEX, KLINE_DAYS)
        mk = market_map(mk_rows)
        print("      大盘交易日 %d 天 (%s ~ %s)" % (len(mk), mk_rows[0]["day"], mk_rows[-1]["day"]))
    except Exception as e:
        print("      ⚠️ 大盘抓取失败: %s" % e)
        mk_rows, mk = [], {}

    print("[2/4] 抓取 %d 只 ETF 日K线 ..." % len(ETFS))
    fmap = {}
    ok = 0
    for code, name in ETFS:
        try:
            rows = fetch_kline(code, KLINE_DAYS)
            fm = factor_map(rows)
            if fm:
                fmap[code] = fm
                ok += 1
        except Exception as e:
            print("      [跳过] %s %s: %s" % (code, name, e))
    print("      成功 %d/%d 只" % (ok, len(ETFS)))
    if not fmap:
        print("❌ 全部抓取失败, 退出")
        return 1

    name_of = dict(ETFS)
    print("[3/4] 逐交易日生成快照 ...")
    # 交易日集合: 以大盘日期为准, 兜底用 ETF 日期并集
    days = sorted(mk.keys()) if mk else sorted({d for fm in fmap.values() for d in fm})
    days = [d for d in days if any(d in fm for fm in fmap.values())]
    if not days:
        print("❌ 无有效交易日")
        return 1

    latest = days[-1]
    written, skipped = 0, 0
    index_days = {}
    for day in days:
        items = []
        for code, fm in fmap.items():
            f = fm.get(day)
            if not f:
                continue
            items.append(dict(f, c=code, n=name_of[code]))
        if not items:
            continue
        items.sort(key=lambda x: x["t"], reverse=True)
        for i, it in enumerate(items):
            it["r"] = i + 1

        m = mk.get(day, {"st": "—", "w": 0, "close": None, "mom": None})
        passers = [x for x in items if x["pass"]]
        top = items[:HOLD_SIGNAL] if True else []
        # 推荐 = 前2名中通过风控的; 若都不通过则为空仓
        holds = [x for x in top if x["pass"]]

        # 指数涨跌(相对上一交易日)
        idx_chg = None
        if mk_rows:
            for i, r in enumerate(mk_rows):
                if r["day"] == day and i > 0:
                    idx_chg = round((r["close"] / mk_rows[i - 1]["close"] - 1) * 100, 2)
                    break

        snap = {
            "d": day,
            "st": m["st"], "w": m["w"],
            "idx": m.get("close"), "idx_chg": idx_chg, "mom": m.get("mom"),
            "n": len(items), "pass": len(passers),
            "items": items,
        }
        p = os.path.join(DATA, "%s.json" % day)
        if os.path.exists(p) and day != latest:
            skipped += 1
        else:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(snap, f, ensure_ascii=False, separators=(",", ":"))
            written += 1

        index_days[day] = {
            "st": m["st"], "w": m["w"], "pass": len(passers), "n": len(items),
            "idx_chg": idx_chg,
            "top": [{"c": x["c"], "n": x["n"], "t": x["t"]} for x in holds],
            "lead": {"n": items[0]["n"], "t": items[0]["t"], "pass": items[0]["pass"]} if items else None,
        }

    print("      写入 %d 个, 跳过已存在 %d 个, 共 %d 个交易日" % (written, skipped, len(days)))

    print("[4/4] 生成索引 ...")
    idx = {
        "updated": now_str,
        "latest": latest,
        "count": len(index_days),
        "range": [days[0], latest],
        "codes": [[c, n] for c, n in ETFS],
        "days": index_days,
    }
    with open(os.path.join(DATA, "index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, separators=(",", ":"))

    # 本地双击兜底: file:// 下浏览器禁止 fetch, 把全部数据打成 JS 变量供页面直接读
    # (该文件已 gitignore, 只用于本机预览)
    bundle = {"index": idx, "days": {}}
    for day in days:
        fp = os.path.join(DATA, "%s.json" % day)
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    bundle["days"][day] = json.load(f)
            except Exception:
                pass
    with open(os.path.join(DATA, "local-bundle.js"), "w", encoding="utf-8") as f:
        f.write("window.__ETF_BUNDLE__=")
        json.dump(bundle, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";")
    print("      本地预览包 local-bundle.js 已生成")

    ld = index_days[latest]
    print("✅ 完成 %s | 共 %d 个交易日 (%s ~ %s) | 最新: %s 大盘%s 通过%d/%d"
          % (now_str, len(index_days), days[0], latest, latest, ld["st"], ld["pass"], ld["n"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
