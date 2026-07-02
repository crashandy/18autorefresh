import streamlit as st
import os
import subprocess
import sys

# 設定網頁標題與風格（必須放在最前面）
st.set_page_config(page_title="18度雞 品项監測系統", page_icon="🐔", layout="wide")
st.title("🐔 18度雞 雲端點餐監測系統")
st.subheader("即時監測：店製品項販售狀態 & 鍋燒連動標籤")

# 【終極動態防呆】完全避開 requirements.txt 衝突錯誤
try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:
    with st.spinner("首次啟動：正在為「18度雞」安裝核心偵測套件（約需 30 秒）..."):
        # 在背景安全下載並安裝 playwright 模組
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright==1.44.0"])
    st.success("核心套件安裝成功！正在重新載入系統...")
    st.rerun()

# 檢查 Playwright 瀏覽器是否真正就緒
cache_path = os.path.expanduser("~/.cache/ms-playwright")
if not os.path.exists(cache_path) or not any("chromium" in f or "shell" in f for f in os.listdir(cache_path)):
    with st.spinner("首次啟動：正在下載雲端瀏覽器核心（約需 1 分鐘）..."):
        # 強制安裝相容的瀏覽器
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
        st.success("瀏覽器環境配置成功！")
        st.rerun()

# --- 環境完全就緒，正式進入 18度雞 監測邏輯 ---
from playwright.sync_api import sync_playwright
from streamlit_autorefresh import st_autorefresh
import time

# 每 5 分鐘自動刷新網頁，確保與後台同步
st_autorefresh(interval=300000, key="datarefresh")

# ==================== 18度雞 完整品項資料庫 ====================
menu_database = {
    "🍜 鍋燒意麵系列": [
        "原味鍋燒", "古早味沙茶", "手作韓式泡菜", "手作黃金泡菜", 
        "人氣奶香牛奶", "經典辣味奶香", "必點重慶辣椒", 
        "泰式酸辣冬蔭功", "馬來西亞叻沙", "南洋檸檬香茅鍋"
    ],
    "🍞 厚奶酥厚片系列": [
        "復刻原味厚奶酥", "可可布朗尼厚奶酥", "宇治抹茶厚奶酥", 
        "流沙花生厚奶酥", "草莓厚奶酥", "芋泥厚奶酥", 
        "蒜香厚奶酥", "鹹蛋黃厚奶酥", "榛果厚奶酥", "咖啡厚奶酥", 
        "伯爵茶厚奶酥", "鐵觀音厚奶酥", "開心果厚奶酥（限定）", "烏龍厚奶酥", "芝麻厚奶酥"
    ],
    "🥤 飲品系列": [
        "玄米綠茶(無糖)", "麥香紅茶(微糖)", "冬瓜茶", "鮮奶紅茶", 
        "鮮奶冬瓜", "可爾必思", "罐裝烏龍", "可樂", "雪碧", "罐裝綠茶"
    ],
    "🍟 宵點炸物系列": [
        "炸物拼盤A內容物：薯條、雞塊、薯餅、小熱狗", 
        "炸物拼盤B內容物：雞米花、洋蔥圈、起司豬排", 
        "炸物拼盤C炸物A + 炸物B", 
        "薯餅", "小熱狗", "洋蔥圈", "薯條", "炸銀絲卷", 
        "原味雞米花", "麥克雞塊", "起司豬排", "卡啦雞腿排"
    ],
    "🥟 私房點心系列": [
        "港式叉燒包(2入)", "香蒸流沙包(2入)", "蟹黃燒賣(3入)", 
        "鮮蝦燒賣(3入)", "糯米珍珠丸(3入)", "香酥腐衣蝦捲(2條)", 
        "酥炸鮮奶馬蹄條(3條)", "酥炸韭菜小春捲(2條)"
    ],
    "🍲 韓式豆腐煲系列": [
        "韓式海陸豆腐粉絲煲", "韓式味噌豆腐粉絲煲"
    ]
}

tag_representative_item = "原味鍋燒"
required_sub_tags = [
    "加蛋", "加起司", "加一份肉4片", "加一份蛤蠣4顆", 
    "加一份魚片2片", "加一份蝦3隻", "升級海陸鍋"
]
# ==============================================================

def check_dudoo_store():
    url = "https://store.dudooeat.com/orderv2/menu/c5e254b96f03475e967c6a96225173e3"
    item_status = {}
    missing_tags = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        
        try:
            page.wait_for_selector(f"text={tag_representative_item}", timeout=15000)
        except:
            pass
        
        # 檢查大品項
        for category, items in menu_database.items():
            item_status[category] = {}
            for item in items:
                element = page.locator(f"text='{item}'").first
                if element.count() > 0:
                    parent_text = element.locator(".. >> .. >> ..").inner_text()
                    if "sold out" in parent_text.lower() or "已售完" in parent_text:
                        item_status[category][item] = "❌ 售完反黑"
                    else:
                        item_status[category][item] = "🟢 正常販售"
                else:
                    item_status[category][item] = "🚫 完全未上架"
                    
        # 檢查客製化連動標籤
        rep_status = item_status["🍜 鍋燒意麵系列"].get(tag_representative_item, "")
        if rep_status == "🟢 正常販售":
            try:
                rep_element = page.locator(f"text='{tag_representative_item}'").first
                rep_element.click()
                time.sleep(1.5)
                
                popup_text = page.locator("body").inner_text()
                for tag in required_sub_tags:
                    if tag not in popup_text:
                        missing_tags.append(f"{tag} (後台未勾選/遺失)")
                    elif f"{tag} 售完" in popup_text or f"{tag}已售完" in popup_text:
                        missing_tags.append(f"{tag} (顯示售完)")
                        
                page.keyboard.press("Escape")
                time.sleep(0.5)
            except Exception as e:
                missing_tags = [f"無法成功點入檢查標籤: {e}"]
        else:
            missing_tags = [f"因代表品項 [{tag_representative_item}] 狀態為 {rep_status}，無法執行內部標籤檢查"]

        browser.close()
    return item_status, missing_tags

# ==================== 網頁前端介面呈現 ====================
with st.spinner("🔄 正在幫「18度雞」巡檢雲端點餐狀態，請稍候..."):
    try:
        store_results, tag_results = check_dudoo_store()
        
        total_missing_items = 0
        for cat, items in store_results.items():
            for item, status in items.items():
                if "🟢" not in status:
                    total_missing_items += 1
        total_missing_tags = len(tag_results)
        
        c1, c2 = st.columns(2)
        c1.metric("大品項異常數（未開/售完）", f"{total_missing_items} 項", delta=total_missing_items, delta_color="inverse")
        c2.metric("鍋燒客製標籤異常數", f"{total_missing_tags} 項", delta=total_missing_tags, delta_color="inverse")
        
        st.divider()
        
        st.markdown("### 🏷️ 鍋燒意麵－加選標籤檢查報告（連動）")
        if tag_results:
            st.error("🚨 **注意！店員漏開或關閉了以下加選標籤：**")
            for msg in tag_results:
                st.markdown(f"⚠️ 鍋燒配料：**{msg}**")
        else:
            st.success("✅ **太棒了！鍋燒意麵的「加蛋、加起司、加肉、加海鮮」等加選區全數正常供應！**")
            
        st.divider()
        st.markdown("### 📋 各大系列大品項即時狀態")
        tabs = st.tabs(list(menu_database.keys()))
        
        for index, (category, items) in enumerate(store_results.items()):
            with tabs[index]:
                st.write(f"以下為【{category}】目前的線上販售狀態：")
                col_left, col_right = st.columns(2)
                item_list = list(items.items())
                mid_point = (len(item_list) + 1) // 2
                
                with col_left:
                    for item, status in item_list[:mid_point]:
                        if "🟢" in status:
                            st.caption(f"{status} ｜ {item}")
                        else:
                            st.markdown(f"**{status} ｜ {item}**")
                with col_right:
                    for item, status in item_list[mid_point:]:
                        if "🟢" in status:
                            st.caption(f"{status} ｜ {item}")
                        else:
                            st.markdown(f"**{status} ｜ {item}**")
                            
    except Exception as e:
        st.error(f"❌ 偵測系統連線失敗，請檢查網路或肚肚網站是否正常。錯誤訊息：{e}")
