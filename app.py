import streamlit as st
import urllib.request
import ssl
from streamlit_autorefresh import st_autorefresh

# 設定網頁標題與風格
st.set_page_config(page_title="18度雞 品項監測系統", page_icon="🐔", layout="wide")
st.title("🐔 18度雞 雲端點餐監測系統")
st.subheader("即時監測：店製品項販售狀態 & 鍋燒連動標籤")

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
        "伯爵茶厚奶酥", "鐵觀音厚奶酥", "開心果厚奶酥", "烏龍厚奶酥", "芝麻厚奶酥"
    ],
    "🥤 飲品系列": [
        "玄米綠茶(無糖)", "麥香紅茶(微糖)", "冬瓜茶", "鮮奶紅茶", 
        "鮮奶冬瓜", "可爾必思", "罐裝烏龍", "可樂", "雪碧", "罐裝綠茶"
    ],
    "🍟 宵點炸物系列": [
        "炸物拼盤A", 
        "炸物拼盤B", 
        "炸物拼盤C", 
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

required_sub_tags = [
    "加蛋", "加起司", "加一份肉4片", "加一份蛤蠣4顆", 
    "加一份魚片2片", "加一份蝦3隻", "升級海陸鍋"
]
# ==============================================================

def check_dudoo_via_html():
    url = "https://store.dudooeat.com/orderv2/menu/c5e254b96f03475e967c6a96225173e3"
    
    # 模擬真實瀏覽器的 Header，繞過部分的阻擋機制
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 忽略 SSL 憑證檢查，防止雲端伺服器握手失敗
    context = ssl._create_unverified_context()
    
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=context) as response:
        # 讀取網頁完整的網頁原始碼並轉成文字字串
        page_html = response.read().decode('utf-8')
        
    item_status = {}
    missing_tags = []
    
    # --- 步驟 1：運用您測試成功的純字串切片大絕招，檢查大品項 ---
    for category, items in menu_database.items():
        item_status[category] = {}
        for item in items:
            item_pos = page_html.find(item)
            
            if item_pos != -1:
                # 往回切片看包裹它的 <div class="mealItem">
                prefix_html = page_html[max(0, item_pos-400):item_pos]
                start_box_pos = prefix_html.rfind('class="mealItem')
                
                if start_box_pos != -1:
                    box_classes = prefix_html[start_box_pos:start_box_pos+120]
                    # 精確命中您提供的 html 缺貨特徵：item-disabled
                    if "item-disabled" in box_classes:
                        item_status[category][item] = "❌ 售完反黑"
                    else:
                        item_status[category][item] = "🟢 正常販售"
                else:
                    # 容錯機制
                    if "order_menu_sold_out" in page_html[max(0, item_pos-200):item_pos+200]:
                        item_status[category][item] = "❌ 售完反黑"
                    else:
                        item_status[category][item] = "🟢 正常販售"
            else:
                item_status[category][item] = "🚫 完全未上架"
                
    # --- 步驟 2：檢查內頁客製化標籤 ---
    # 因為沒有瀏覽器點擊，我們直接在全網頁 HTML 中搜尋客製化標籤的文字
    # 肚肚系統的客製化標籤如果售完，通常會在該標籤的原始碼附近出現 "disabled" 或 "sold-out"
    for tag in required_sub_tags:
        tag_pos = page_html.find(tag)
        if tag_pos == -1:
            missing_tags.append(f"{tag} (後台未勾選/遺失)")
        else:
            # 檢查標籤文字前後 150 個字元內有沒有包含售完或停用特徵
            tag_surrounding = page_html[max(0, tag_pos-150):tag_pos+150]
            if "sold" in tag_surrounding.lower() or "disabled" in tag_surrounding.lower():
                missing_tags.append(f"{tag} (顯示售完)")
                
    return item_status, missing_tags

# ==================== 網頁前端介面呈現 ====================
with st.spinner("🔄 正在透過安全文字通道巡檢「18度雞」點餐畫面..."):
    try:
        store_results, tag_results = check_dudoo_via_html()
        
        # 統計異常
        total_missing_items = 0
        category_error_counts = {}
        for cat, items in store_results.items():
            error_in_cat = 0
            for item, status in items.items():
                if "🟢" not in status:
                    total_missing_items += 1
                    error_in_cat += 1
            category_error_counts[cat] = error_in_cat
            
        total_missing_tags = len(tag_results)
        
        # 頂部數據看板
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
        
        tab_titles = [f"{cat} (❌ {category_error_counts.get(cat, 0)}項售完)" if category_error_counts.get(cat, 0) > 0 else f"{cat} (🟢 全數正常)" for cat in menu_database.keys()]
        tabs = st.tabs(tab_titles)
        
        for index, (category, items) in enumerate(store_results.items()):
            with tabs[index]:
                err_count = category_error_counts.get(category, 0)
                if err_count > 0:
                    st.warning(f"⚠️ 注意：此分類目前有 **{err_count}** 個品項處於售完或未上架狀態！")
                else:
                    st.success("🟢 完美！此分類所有品項皆在線上正常販售中。")
                    
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
        st.error(f"❌ 偵測系統連線失敗。錯誤訊息：{e}")
