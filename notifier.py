# -*- coding: utf-8 -*-
import os
import resend
from datetime import datetime

def send_stock_report(market_name, img_data, report_df, text_reports):
    """
    發送包含 9 張分布圖與智慧技術線圖連結的專業電子郵件
    """
    # 1. 檢查 API Key
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("❌ 錯誤：找不到環境變數 RESEND_API_KEY，郵件發送中斷。")
        return
    resend.api_key = api_key

    now_str = datetime.now().strftime("%Y-%m-%d")
    
    # 2. 判斷市場屬性（決定連結目標）
    market_upper = market_name.upper()
    is_us = "美國" in market_upper or "US" in market_upper
    is_hk = "香港" in market_upper or "HK" in market_upper

    # 3. 建立 Top 50 連結區塊邏輯
    def get_top50_links(df, col_name):
        if col_name not in df.columns:
            return "目前無數據"
        
        # 依照漲幅排序取前 50 名
        top50 = df.sort_values(by=col_name, ascending=False).head(50)
        links = []
        
        for _, r in top50.iterrows():
            ticker = r["Ticker"]
            # 根據市場生成對應連結
            if is_us:
                url = f"https://stockcharts.com/sc3/ui/?s={ticker}"
            elif is_hk:
                # 港股 AASTOCKS 需要 5 位數
                clean_code = ticker.replace(".HK", "").strip().zfill(5)
                url = f"https://www.aastocks.com/tc/stocks/quote/quick-quote.aspx?symbol={clean_code}"
            else:
                # 台股 玩股網
                clean_tkr = ticker.split('.')[0]
                url = f"https://www.wantgoo.com/stock/{clean_tkr}/technical-chart"
            
            # 顯示名稱 (優先使用 Full_Name)
            display_name = r.get("Full_Name", ticker)
            links.append(f'<a href="{url}" style="text-decoration:none; color:#0366d6;">{ticker}({display_name})</a>')
        
        return " | ".join(links)

    # 4. 組合 HTML 郵件內容
    # 使用 CSS 讓郵件在手機與電腦端看起來都更專業
    html_content = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; max-width: 850px; margin: auto; border: 1px solid #eee; padding: 20px; border-radius: 10px;">
        <h2 style="color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px;">
            🚀 {market_name} 全方位市場監控報表
        </h2>
        <p style="color: #7f8c8d; font-size: 14px;">報告生成時間: {now_str}</p>
        
        <div style="background-color: #fdfefe; border-left: 5px solid #e74c3c; padding: 10px; margin: 20px 0; font-size: 14px;">
            💡 提示：點擊下方表格中的<b>股票代號</b>，可直接跳轉至該市場的專業技術線圖（{'StockCharts' if is_us else 'AASTOCKS' if is_hk else '玩股網'}）。
        </div>
    """
    
    # 插入 9 張分布圖 (垂直排列)
    for img in img_data:
        html_content += f"<h3 style='color: #2980b9; margin-top: 30px;'>📍 {img['label']}</h3>"
        html_content += f'<img src="cid:{img["id"]}" style="width:100%; max-width:800px; border-radius: 5px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">'

    # 插入分箱清單文字
    html_content += "<div style='background-color: #f4f7f6; padding: 15px; border-radius: 8px; margin-top: 40px;'>"
    for period, report in text_reports.items():
        p_name = {"Week": "週", "Month": "月", "Year": "年"}.get(period, period)
        html_content += f"<h4 style='color: #16a085; margin-bottom: 5px;'>📊 {p_name}K 報酬分布明細 (含飆股清單)</h4>"
        html_content += f"<pre style='background-color: #ffffff; padding: 10px; border: 1px solid #ddd; font-size: 12px; white-space: pre-wrap; word-wrap: break-word;'>{report}</pre>"
    html_content += "</div>"

    # 插入 Top 50 飆股區塊
    html_content += f"""
        <hr style="border: 0; border-top: 1px solid #eee; margin: 40px 0;">
        <h4 style="color: #c0392b;">🔥 本週表現最強動能 Top 50</h4>
        <div style="line-height: 2; font-size: 13px; color: #34495e;">
            {get_top50_links(report_df, 'Week_High')}
        </div>
        <p style="margin-top: 50px; font-size: 12px; color: #bdc3c7; text-align: center;">
            此報表為自動生成，僅供研究參考，不構成投資建議。
        </p>
    </div>
    """

    # 5. 準備圖片附件 (Inline Embedding)
    attachments = []
    for img in img_data:
        with open(img['path'], "rb") as f:
            attachments.append({
                "content": list(f.read()),
                "filename": f"{img['id']}.png",
                "content_id": img['id'],
                "disposition": "inline"
            })

    # 6. 執行寄送
    # 請確保收件人正確
<<<<<<< HEAD
    to_emails = ["kadelat@mail.com"]
=======
    to_emails = ["kadelat@gmail.com"]
>>>>>>> 91540c091317097fcb0dd5eefa1603674d91a779

    try:
        resend.Emails.send({
            "from": "StockMonitor <onboarding@resend.dev>",
            "to": to_emails,
            "subject": f"🚀 {market_name} 監控報告 - {now_str}",
            "html": html_content,
            "attachments": attachments
        })
        print(f"✅ 郵件發送成功！市場：{market_name}")
    except Exception as e:

        print(f"❌ 郵件發送失敗 ({market_name}): {e}")
