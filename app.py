import streamlit as st
import fastf1 as ff1
import pandas as pd
import plotly.express as px

# --- ページ設定 ---
# ページのレイアウトを「ワイド（幅広）」に設定
st.set_page_config(layout="wide")

# --- アプリのタイトル ---
st.title("F1 Data Analysis Dashboard 🏎️")
st.header("Yuki Tsunoda - Lap Time Analysis (Suzuka 2024)")

# --- データ取得と分析（Notebookのコードとほぼ同じ）---

# 1. キャッシュを有効にする
ff1.Cache.enable_cache('./cache') 

# 2. セッションの読み込み (エラー防止のため@st.cache_dataを使う)
# Streamlitはスクリプトを頻繁に再実行するため、重い処理はキャッシュします
@st.cache_data
def load_session_data(year, race, session_type):
    session = ff1.get_session(year, race, session_type)
    session.load()
    laps = session.laps
    return laps

try:
    # 鈴鹿(4)の決勝(R)データを読み込む
    laps = load_session_data(2024, 4, 'R')

    # 3. 角田選手(TSU)のデータだけを抽出
    driver_laps = laps.pick_driver('TSU')

    # 4. LapTimeを秒（数値）に変換
    driver_laps['LapTimeSeconds'] = driver_laps['LapTime'].dt.total_seconds()

    # 5. 遅いラップ（ノイズ）を除外
    driver_laps_cleaned = driver_laps.loc[driver_laps['LapTimeSeconds'] < 110]

    # 6. Plotlyでグラフを作成
    fig = px.scatter(driver_laps_cleaned, 
                     x='LapNumber',
                     y='LapTimeSeconds',
                     color='Compound',
                     hover_data=['Stint', 'TyreLife'])

    fig.update_layout(title="Yuki Tsunoda - Lap Time Analysis (Suzuka 2024)",
                      xaxis_title="Lap Number",
                      yaxis_title="Lap Time (Seconds)")

    # --- Streamlitでの表示 ---
    # 7. Notebookの fig.show() の代わりに、st.plotly_chart() を使う
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"データの読み込み中にエラーが発生しました: {e}")
    st.info("FastF1のデータソースが利用できない可能性があります。")