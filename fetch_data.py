#!/usr/bin/env python3
"""
全天候策略持仓数据拉取脚本
强制使用 LongPort Python SDK（v3）
"""

import os
import json
import datetime

APP_KEY = os.environ.get("LONGPORT_APP_KEY", "")
APP_SECRET = os.environ.get("LONGPORT_APP_SECRET", "")
ACCESS_TOKEN = os.environ.get("LONGPORT_ACCESS_TOKEN", "")

TARGET_ETFS = ["YMAG.US", "SPDW.US", "IAUI.US", "GUNR.US", "DBMF.US"]

def sdk_config():
    """构造 SDK Config"""
    from longport.openapi import Config
    return Config(app_key=APP_KEY, app_secret=APP_SECRET, access_token=ACCESS_TOKEN)

def run():
    import asyncio
    from longport.openapi import Config, TradeContext, QuoteContext

    async def _fetch():
        config = Config(app_key=APP_KEY, app_secret=APP_SECRET, access_token=ACCESS_TOKEN)
        trade_ctx = TradeContext(config)
        quote_ctx = QuoteContext(config)

        # 1. 获取持仓（所有标的）
        print("=== 获取持仓 ===")
        positions = await trade_ctx.stock_positions()
        print(f"总持仓数量: {len(positions)}")

        # 打印原始数据结构
        for ch in positions:
            print(f"  {ch.stock_name} ({ch.symbol}): 数量={ch.quantity}, 成本={ch.cost_price}, 市值={ch.market_value}")

        # 2. 过滤目标 ETF
        target = []
        for ch in positions:
            if any(t in ch.symbol for t in TARGET_ETFS):
                target.append(ch)

        print(f"目标 ETF: {[ch.symbol for ch in target]}")

        # 3. 获取实时行情
        symbols = [ch.symbol for ch in target]
        quotes = {}
        if symbols:
            print("=== 获取行情 ===")
            qresp = await quote_ctx.quote(symbols)
            for q in qresp:
                quotes[q.symbol] = q
                print(f"  {q.symbol}: 现价={q.last_done}, 涨跌={q.change_ratio}")

        # 4. 组装数据
        holdings = []
        total_cost = 0
        total_value = 0
        total_pnl = 0

        for ch in target:
            sym = ch.symbol
            qty = float(ch.quantity)
            cost_price = float(ch.cost_price)
            market_value = float(ch.market_value)
            quote = quotes.get(sym)
            current_price = float(quote.last_done) if quote and quote.last_done else cost_price

            total_val = current_price * qty
            pnl_amount = total_val - (cost_price * qty)
            pnl_pct = (pnl_amount / (cost_price * qty) * 100) if cost_price * qty else 0

            holding = {
                "symbol": sym,
                "name": ch.stock_name,
                "quantity": qty,
                "cost_price": round(cost_price, 4),
                "cost_value": round(cost_price * qty, 2),
                "current_price": round(current_price, 4),
                "current_value": round(total_val, 2),
                "pnl_amount": round(pnl_amount, 2),
                "pnl_pct": round(pnl_pct, 2),
                "currency": "USD",
                "last_updated": datetime.datetime.now().astimezone().isoformat(),
            }
            holdings.append(holding)

            total_cost += cost_price * qty
            total_value += total_val
            total_pnl += pnl_amount

        # 5. 保存
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

        output_path = os.environ.get("OUTPUT_PATH", "data/latest.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n=== 汇总 ===")
        print(f"总投资: ${total_cost:.2f}")
        print(f"当前价值: ${total_value:.2f}")
        if total_cost:
            print(f"总盈亏: ${total_pnl:.2f} ({total_pnl/total_cost*100:.2f}%)")
        print(f"数据已保存到 {output_path}")
        print("=== 完成 ===")

    asyncio.run(_fetch())

if __name__ == "__main__":
    print(f"=== LongPort 数据拉取开始 {datetime.datetime.now().astimezone().isoformat()} ===")
    run()
