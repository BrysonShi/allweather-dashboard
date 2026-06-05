#!/usr/bin/env python3
"""
全天候策略持仓数据拉取脚本
从 LongPort API 获取持仓和行情数据
"""

import os
import json
import datetime

# 尝试使用 SDK，fallback 到 HTTP
try:
    import urllib.request
    import urllib.error
    USE_SDK = False
except ImportError:
    USE_SDK = False

# ====== 配置 ======
APP_KEY = os.environ.get("LONGPORT_APP_KEY", "")
APP_SECRET = os.environ.get("LONGPORT_APP_SECRET", "")
ACCESS_TOKEN = os.environ.get("LONGPORT_ACCESS_TOKEN", "")
BASE_URL = "https://openapi.longportapp.com"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

# 目标 ETF 列表
TARGET_ETFS = ["YMAG.US", "SPDW.US", "IAUI.US", "GUNR.US", "DBMF.US"]

def http_get(path):
    """HTTP 方式调用 API"""
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        print(f"HTTP Error {e.code}: {body}")
        return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def try_sdk():
    """尝试用 SDK 调用"""
    try:
        from longport.openapi import Config, QuoteContext
        import asyncio

        async def get_quotes():
            config = Config.from_env()
            ctx = QuoteContext(config)
            resp = await ctx.quote(TARGET_ETFS)
            return resp

        return asyncio.run(get_quotes())
    except ImportError:
        return None
    except Exception as e:
        print(f"SDK error: {e}")
        return None

def get_positions():
    """获取持仓列表"""
    data = http_get("/v1/asset/positions")
    if not data:
        return []
    if isinstance(data, dict):
        return data.get("positions", []) or data.get("data", []) or []
    if isinstance(data, list):
        return data
    return []

def get_quotes_http(symbols):
    """通过 HTTP 获取行情"""
    sym_str = ",".join(symbols)
    data = http_get(f"/v1/quote/quotes?symbols={sym_str}")
    if not data:
        return {}
    if isinstance(data, dict):
        return data.get("quotes", {}) or data.get("data", {})
    return {}

def filter_target_positions(positions):
    """过滤目标 ETF 持仓"""
    result = []
    for pos in positions:
        symbol = pos.get("symbol", "")
        if any(t in symbol for t in TARGET_ETFS):
            result.append({
                "symbol": symbol,
                "name": pos.get("name", symbol),
                "quantity": pos.get("quantity", 0),
                "available_quantity": pos.get("available_quantity", 0),
                "cost_price": pos.get("cost_price", 0),
                "market_value": pos.get("market_value", 0),
                "currency": pos.get("currency", "USD"),
            })
    return result

def calculate_pnl(pos, quote):
    """计算盈亏"""
    qty = pos.get("quantity", 0)
    cost = pos.get("cost_price", 0)
    current_price = quote.get("last_done", 0) if quote else 0
    if not current_price and pos.get("market_value") and qty:
        current_price = pos.get("market_value", 0) / qty

    if not current_price or not qty:
        return 0, 0, 0

    total_cost = cost * qty
    current_value = current_price * qty
    pnl_amount = current_value - total_cost
    pnl_pct = (pnl_amount / total_cost * 100) if total_cost else 0
    return round(pnl_amount, 2), round(pnl_pct, 2), round(current_value, 2)

def main():
    print("=== LongPort 数据拉取开始 ===")
    print(f"时间: {datetime.datetime.now().astimezone().isoformat()}")

    # 1. 获取持仓
    positions = get_positions()
    print(f"总持仓数量: {len(positions)}")
    print(f"持仓数据: {json.dumps(positions[:2], ensure_ascii=False)[:300]}")

    # 2. 过滤目标 ETF
    target_positions = filter_target_positions(positions)
    print(f"目标 ETF 持仓: {[p['symbol'] for p in target_positions]}")

    # 3. 获取实时行情
    symbols = [p["symbol"] for p in target_positions]
    quotes = get_quotes_http(symbols) if symbols else {}
    print(f"获取行情: {list(quotes.keys())}")
    print(f"行情数据示例: {json.dumps(list(quotes.values())[:1], ensure_ascii=False)[:300]}")

    # 4. 组装数据
    holdings = []
    total_cost = 0
    total_value = 0
    total_pnl = 0

    for pos in target_positions:
        sym = pos["symbol"]
        quote = quotes.get(sym, {})
        pnl_amt, pnl_pct, cur_val = calculate_pnl(pos, quote)
        cost_val = pos["cost_price"] * pos["quantity"]

        holding = {
            "symbol": sym,
            "name": pos["name"],
            "quantity": pos["quantity"],
            "cost_price": pos["cost_price"],
            "cost_value": round(cost_val, 2),
            "current_price": quote.get("last_done", pos["cost_price"]) or pos["cost_price"],
            "current_value": cur_val or pos.get("market_value", 0),
            "pnl_amount": pnl_amt,
            "pnl_pct": pnl_pct,
            "currency": pos["currency"],
            "last_updated": datetime.datetime.now().astimezone().isoformat(),
        }
        holdings.append(holding)

        total_cost += cost_val
        total_value += (cur_val or pos.get("market_value", 0))
        total_pnl += pnl_amt

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

if __name__ == "__main__":
    main()
