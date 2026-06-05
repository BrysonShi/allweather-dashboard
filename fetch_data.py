#!/usr/bin/env python3
"""
全天候策略持仓数据拉取脚本
使用 LongPort Python SDK v3
"""

import os
import json
import datetime

APP_KEY = os.environ.get("LONGPORT_APP_KEY", "")
APP_SECRET = os.environ.get("LONGPORT_APP_SECRET", "")
ACCESS_TOKEN = os.environ.get("LONGPORT_ACCESS_TOKEN", "")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "data/latest.json")
TARGET_ETFS = ["YMAG.US", "SPDW.US", "IAUI.US", "GUNR.US", "DBMF.US"]

def run():
    from longport.openapi import Config, TradeContext, QuoteContext

    config = Config(app_key=APP_KEY, app_secret=APP_SECRET, access_token=ACCESS_TOKEN)
    trade_ctx = TradeContext(config)
    quote_ctx = QuoteContext(config)

    print("=== 获取持仓 ===")
    resp = trade_ctx.stock_positions()
    channels = resp.channels
    all_positions = []
    for ch in channels:
        all_positions.extend(getattr(ch, 'positions', []))
    print(f"总持仓数量: {len(all_positions)}")
    for pos in all_positions:
        print(f"  [{pos.symbol}] {pos.symbol_name} | qty={pos.quantity} | cost=${pos.cost_price}")

    target = [pos for pos in all_positions if any(t in pos.symbol for t in TARGET_ETFS)]
    print(f"目标 ETF: {[pos.symbol for pos in target]}")

    symbols = [pos.symbol for pos in target]
    quotes = {}
    if symbols:
        print("=== 获取行情 ===")
        qresp = quote_ctx.quote(symbols)  # 同步方法
        for q in qresp:
            quotes[q.symbol] = q
            print(f"  {q.symbol}: ${q.last_done}")

    holdings = []
    total_cost = 0
    total_value = 0
    total_pnl = 0

    # 获取现金余额
    print("\n=== 获取账户现金余额 ===")
    cash_balance = 0.0
    try:
        bal_resp = trade_ctx.account_balance()
        for bal in bal_resp:
            currency = getattr(bal, 'currency', '')
            if currency.upper() == 'USD':
                cash_balance = float(getattr(bal, 'available_cash', 0))
                print(f"  USD 可用现金: ${cash_balance} (withdraw=${getattr(bal, 'withdraw_cash', 0)}, frozen={getattr(bal, 'frozen_cash', 0)}, settling={getattr(bal, 'settling_cash', 0)})")
            else:
                print(f"  {currency} 可用现金: {getattr(bal, 'available_cash', 0)}")
    except Exception as e:
        print(f"  获取现金余额失败: {e}")

    for pos in target:
        sym = pos.symbol
        qty = float(pos.quantity)
        cost_price = float(pos.cost_price)
        stock_name = pos.symbol_name
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
        "cash_balance": round(cash_balance, 2),
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
