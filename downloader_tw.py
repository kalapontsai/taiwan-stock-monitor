# -*- coding: utf-8 -*-
import os
import time
import requests
import pandas as pd
import yfinance as yf
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from pathlib import Path

# ========== 核心參數設定 ==========
MARKET_CODE = "tw-share"
DATA_SUBDIR = "dayK"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", MARKET_CODE, DATA_SUBDIR)

MAX_WORKERS = 4 
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

def log(msg: str):
    print(f"{pd.Timestamp.now():%H:%M:%S}: {msg}")

def get_full_stock_list():
    url_configs = [
        {'name': 'listed', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?market=1&issuetype=1&Page=1&chklike=Y', 'suffix': '.TW'},
        {'name': 'dr', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=1&issuetype=J&industry_code=&Page=1&chklike=Y', 'suffix': '.TW'},
        {'name': 'otc', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?market=2&issuetype=4&Page=1&chklike=Y', 'suffix': '.TWO'},
        {'name': 'etf', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=1&issuetype=I&industry_code=&Page=1&chklike=Y', 'suffix': '.TW'},
        {'name': 'rotc', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=E&issuetype=R&industry_code=&Page=1&chklike=Y', 'suffix': '.TWO'},
        {'name': 'tw_innovation', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=C&issuetype=C&industry_code=&Page=1&chklike=Y', 'suffix': '.TW'},
        {'name': 'otc_innovation', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=A&issuetype=C&industry_code=&Page=1&chklike=Y', 'suffix': '.TWO'},
    ]
    all_items = []
    log("📡 正在獲取各市場清單...")
    for cfg in url_configs:
        try:
            resp = requests.get(cfg['url'], timeout=15)
            df_list = pd.read_html(StringIO(resp.text), header=0)
            if not df_list: continue
            df = df_list[0]
            for _, row in df.iterrows():
                code = str(row['有價證券代號']).strip()
                name = str(row['有價證券名稱']).strip()
                if code and '有價證券' not in code:
                    # 這裡確保格式統一
                    all_items.append(f"{code}{cfg['suffix']}&{name}")
        except: continue
    return list(set(all_items))

def download_stock_data(item):
    """強化解析與報錯診斷"""
    yf_tkr = "ParseError"
    try:
        # ✅ 修正點 1: 使用 maxsplit=1，防止名稱中有 & 導致拆分失敗
        parts = item.split('&', 1)
        if len(parts) < 2:
            return {"status": "error", "tkr": item, "msg": "Format error (missing &)"}
        
        yf_tkr, name = parts
        # 移除檔名非法字元
        safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '_', '-')]).strip()
        out_path = os.path.join(DATA_DIR, f"{yf_tkr}_{safe_name}.csv")
        
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            return {"status": "exists", "tkr": yf_tkr}

        tk = yf.Ticker(yf_tkr)
        # ✅ 修正點 2: 加入超時設定，防止網路卡死
        hist = tk.history(period="2y", timeout=10)
        
        if hist is not None and not hist.empty:
            hist.reset_index(inplace=True)
            hist.columns = [c.lower() for c in hist.columns]
            hist.to_csv(out_path, index=False, encoding='utf-8-sig')
            return {"status": "success", "tkr": yf_tkr}
        else:
            return {"status": "empty", "tkr": yf_tkr}
    except Exception as e:
        # ✅ 修正點 3: 捕捉真實錯誤類別 (例如: 網路斷線, 代號無效)
        return {"status": "error", "tkr": yf_tkr, "msg": str(e)}

def main():
    items = get_full_stock_list()
    log(f"🚀 開始深度稽核任務，目標總數: {len(items)}")
    
    stats = {"success": 0, "exists": 0, "empty": 0, "error": 0}
    error_details = {} # 用來分類錯誤原因

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_stock_data, it): it for it in items}
        pbar = tqdm(total=len(items), desc="下載進度")
        
        for future in as_completed(futures):
            res = future.result()
            s = res["status"]
            stats[s] += 1
            if s == "error":
                err_msg = res.get("msg", "Unknown Error")
                # 簡化錯誤訊息進行分類統計
                short_msg = err_msg[:50] 
                error_details[short_msg] = error_details.get(short_msg, 0) + 1
            pbar.update(1)
        pbar.close()
    
    print("\n" + "="*50)
    log("📊 修正版下載稽核報告:")
    print(f"   - ✅ 成功下載: {stats['success']}")
    print(f"   - 📁 原本已存在: {stats['exists']}")
    print(f"   - 🔍 Yahoo無資料 (Empty): {stats['empty']}")
    print(f"   - ❌ 執行錯誤 (Error): {stats['error']}")
    
    if error_details:
        print("\n⚠️ 錯誤原因細分統計:")
        for msg, count in sorted(error_details.items(), key=lambda x: x[1], reverse=True):
            print(f"   - [{count}次]: {msg}")
    
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
