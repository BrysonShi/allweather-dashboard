#!/usr/bin/env python3
"""
全天候策略持仓数据拉取脚本
使用 LongPort Python SDK v3
"""

import os
import json
import asyncio
import datetime

APP_KEY = os.environ.get("LONGPORT_APP_KEY", "")
APP_SECRET = os.environ.get("LONGPORT_APP_SECRET", "")
ACCESS_TOKEN = os.environ.get("LONGPORT_ACCESS_TOKEN", "")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "data/latest.json")
TARGET_ETFS = ["YMAG.US", "SPDW.US", "IAUI.US", "GUNR.US", "DBMF.US"]

def fetch_positions(trade_ctx):
    """获取持仓（同步方法）"""
    resp = trade_ctx.stock_positions()
    return resp.channels  # StockPositionsResponse.channels

def fetch_quotes(quote_ctx, symbols):
    """获取行情（async 方法）"""
    async def _inner():
        return await quote_ctx.quote(symbols)
    return asyncio.get_event_loop().run_until_complete(_inner())

async def async_fetch_quotes(quote_ctx, symbols):
    """获取行情（async）"""
    return await quote_ctx.quote(symbols)

def run():
    from longport.openapi import Config, TradeContext, QuoteContext

    config = Config(app_key=APP_KEY, app_secret=APP_SECRET, access_token=ACCESS_TOKEN)
    trade_ctx = TradeContext(config)
    quote_ctx = QuoteContext(config)

    print("=== 获取持仓 ===")
    try:
        channels = fetch_positions(trade_ctx)
    except Exception as e:
        print(f"获取持仓失败: {e}")
        channels = []
    print(f"总持仓数量: {len(channels)}")

    # 打印原始数据结构以便调试
    for ch in channels:
        print(f"  持仓对象: {ch}")
        print(f"  类型: {type(ch)}, dir: {[a for a in dir(ch) if not a.startswith('_')]}")

    # 过滤目标 ETF
    target = []
    for ch in channels:
        sym = getattr(ch, 'symbol', str(ch))
        if any(t in sym for t in TARGET_ETFS):
            target.append(ch)

    print(f"目标 ETF: {[getattr(ch, 'symbol', ch) for ch in target]}")

    # 获取实时行情
    symbols = [getattr(ch, 'symbol', str(ch)) for ch in target]
    quotes = {}
    if symbols:
        print("=== 获取行情 ===")
        try:
            qresp = asyncio.run(async_fetch_quotes(quote_ctx, symbols))
            for q in qresp:
                quotes[q.symbol] = q
                print(f"  {q.symbol}: ${q.last_done} ({q.change_ratio*100:.2f}%)")
        except Exception as e:
            print(f"获取行情失败: {e}")

    # 组装数据
    holdings = []
    total_cost = 0
    total_value = 0
    total_pnl = 0

    for ch in target:
        sym = getattr(ch, 'symbol', str(ch))
        qty = float(getattr(ch, 'quantity', 0))
        cost_price = float(getattr(ch, 'cost_price', 0))
        stock_name = getattr(ch, 'stock_name', sym)
        quote = quotes.get(sym)
        current_price = float(quote.last_done) if quote and quote.last_done else cost_price

        cost_val = cost_price * qty
        cur_val = current_price * qty
        pnl_amount = cur_val - cost_val
        pnl_pct = (pnl_amount / cost_val * 100) if cost_val else 0

        holdings.append({
            "symbol": sym,
            "name": stock_name,
            "quantity": qty,
            "cost_price": round(cost_price, 4),
            "cost_value": round(cost_val, 2),
            "current_price": round(current_price, 4),
            "current_value": round(cur_val, 2),
            "pnl_amount": round(pnl_amount, 2),
            "pnl_pct": round(pnl_pct, 2),
            "currency": "USD",
            "last_updated": datetime.datetime.now().astimezone().isoformat(),
        })

        total_cost += cost_val
        total_value += cur_val
        total_pnl += pnl_amount

    result = {
        "updated_at": datetime.datetime.now().astimezone().isoformat(),
        "account_currency": "USD",
        "total_invested": round(total_cost, 2),
        "total_current_value": round(total_value, 2),
        "total_pnl_amount": round(total_pnl, 2),
        "total_pnl_pct": round((total_pnl / total_cost * 100) if total_cost else 0, 2),
        "holdings": holdings,
        "allocation": {
            "total_budget_usd": 1500,
            "target": {
                "YMAG.US": 0.40,
                "SPDW.US": 0.15,
                "IAUI.US": 0.075,
                "GUNR.US": 0.075,
                "DBMF.US": 0.30,
            }
        }
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n=== 汇总 ===")
    print(f"总投资: ${total_cost:.2f}")
    print(f"当前价值: ${total_value:.2f}")
    if total_cost:
        print(f"总盈亏: ${total_pnl:.2f} ({total_pnl/total_cost*100:.2f}%)")
    print(f"已保存到 {OUTPUT_PATH}")
    print("=== 完成 ===")

if __name__ == "__main__":
    print(f"=== 开始 {datetime.datetime.now().astimezone().isoformat()} ===")
    run()
