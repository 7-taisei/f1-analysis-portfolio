import streamlit as st
import fastf1 as ff1
import pandas as pd
from sklearn.linear_model import LinearRegression 
import numpy as np 
import re 
from typing import List, Any 
from fastf1.core import SessionResults 
import plotly.express as px

# --- ページ設定 ---
st.set_page_config(layout="wide")

# --- タイヤ色の定義 (最終決定版) ---
TYRE_COLORS = {
    'SOFT': '#dc143c', 'MEDIUM': '#ffd700', 'HARD': '#66d6fb',
    'INTERMEDIATE': '#4CAF50', 'WET': '#0D47A1'
}

# --- アプリのタイトル ---
st.title("F1 Data Analysis Dashboard 🏎️")

# --- サイドバー (フィルター) ---
st.sidebar.header("Filter Options ⚙️")

# (年の選択)
supported_years = [2024, 2023, 2022]
selected_year = st.sidebar.selectbox("Select Year:", supported_years)

# (レーススケジュールの動的取得)
@st.cache_data
def get_race_schedule(year):
    try:
        schedule = ff1.get_event_schedule(year, include_testing=False)
        return schedule
    except Exception as e:
        st.sidebar.error(f"Error fetching {year} schedule: {e}")
        return pd.DataFrame()

schedule_df = get_race_schedule(selected_year)
if schedule_df.empty:
    st.sidebar.error(f"{selected_year}年のレースデータが見つかりません。")
    selected_race = None
    selected_round = None
else:
    race_names_list = schedule_df['OfficialEventName'].tolist()
    default_race_name = 'Japanese Grand Prix' if 'Japanese Grand Prix' in race_names_list else race_names_list[0]
    selected_race = st.sidebar.selectbox("Select Race:", race_names_list, index=race_names_list.index(default_race_name))
    selected_round = schedule_df.loc[schedule_df['OfficialEventName'] == selected_race, 'RoundNumber'].iloc[0]

# (セッションの動的取得)
@st.cache_data
def get_event_sessions(year, round_number):
    if round_number is None: return []
    try: rn_int = int(round_number)
    except (ValueError, TypeError): return []
    try:
        event = ff1.get_event(year, rn_int) 
        session_keys = ['Session1', 'Session2', 'Session3', 'Session4', 'Session5']
        sessions_from_event = [event[key] for key in session_keys if event[key]]
        session_order = {'Practice 1': 1, 'Practice 2': 2, 'Practice 3': 3, 'Sprint Shootout': 4, 'Sprint Qualifying': 4.5, 'Qualifying': 5, 'Sprint': 6, 'Race': 7, 'FP1': 1, 'FP2': 2, 'FP3': 3, 'SQ': 4, 'Q': 5, 'S': 6, 'R': 7}
        sessions_sorted = sorted([s for s in sessions_from_event if s in session_order], key=lambda s: session_order[s])
        return sessions_sorted
    except Exception as e:
        st.sidebar.warning(f"セッション取得エラー (Y: {year}, R: {rn_int}): {e}")
        return []

session_names_list = get_event_sessions(selected_year, selected_round)
if not session_names_list:
    st.sidebar.warning("このGPのセッション情報が見つかりません。")
    selected_session = None
else:
    default_session = 'Race' if 'Race' in session_names_list else session_names_list[-1]
    selected_session = st.sidebar.selectbox("Select Session:", session_names_list, index=list(session_names_list).index(default_session) if default_session in session_names_list else 0)

# (データ取得)
@st.cache_data
def load_session_data(year, race_name, session_name):
    if not all([year, race_name, session_name]): return None, None
    try:
        session = ff1.get_session(year, race_name, session_name)
        session.load()
        return session.laps, session.results
    except Exception as e:
        st.error(f"データ取得エラー: {year} {race_name} '{session_name}' - {e}")
        return None, None

# --- メイン処理 ---
laps, results = load_session_data(selected_year, selected_race, selected_session)


# --- Deg 分析のためのヘルパー関数 (キャッシュを削除し、引数をPandas DataFrameに限定) ---
# ★★★ @st.cache_data を削除 ★★★
def calculate_advanced_deg(laps_df: pd.DataFrame, results_df: pd.DataFrame):
    from sklearn.linear_model import LinearRegression
    STARTING_FUEL_KG = 110.0
    FUEL_BURN_RATE_KG_PER_LAP = 1.6
    FUEL_EFFECT_SEC_PER_KG = 0.03
    TRACK_EVO_EFFECT_SEC_PER_LAP = 0.01

    # LapsがFastF1のLapsオブジェクトの場合、Pandasに変換
    if not isinstance(laps_df, pd.DataFrame):
         laps_df = pd.DataFrame(laps_df.to_dict()) # 最も安全な変換方法
         # Timedeltaを復元
         for col in ['LapTime', 'PitOutTime', 'PitInTime', 'Sector1Time', 'Sector2Time', 'Sector3Time', 'Time']:
            if col in laps_df.columns:
                laps_df[col] = pd.to_timedelta(laps_df[col])


    laps_with_team = pd.merge(
        laps_df, results_df[['Abbreviation', 'TeamName']], 
        left_on='Driver', right_on='Abbreviation', how='left'
    )
    clean_laps = laps_with_team.loc[
        (laps_with_team['PitInTime'].isna()) & (laps_with_team['PitOutTime'].isna()) & 
        (laps_with_team['TrackStatus'] == '1') & (laps_with_team['LapNumber'] > 1)
    ].dropna(subset=['LapTime']).copy()
    
    clean_laps['LapTimeSeconds'] = clean_laps['LapTime'].dt.total_seconds()
    clean_laps['FuelLoad_KG'] = STARTING_FUEL_KG - (clean_laps['LapNumber'] * FUEL_BURN_RATE_KG_PER_LAP)
    clean_laps['FuelPenalty_sec'] = clean_laps['FuelLoad_KG'] * FUEL_EFFECT_SEC_PER_KG
    clean_laps['TrackEvo_Gain_sec'] = (clean_laps['LapNumber'] - 1) * TRACK_EVO_EFFECT_SEC_PER_LAP
    clean_laps['FullyCorrected_LapTimeSeconds'] = (
        clean_laps['LapTimeSeconds'] - clean_laps['FuelPenalty_sec'] + clean_laps['TrackEvo_Gain_sec']
    )
    
    deg_data: List[Any] = []
    
    for team in clean_laps['TeamName'].unique():
        for compound in clean_laps['Compound'].unique():
            subset = clean_laps.loc[(clean_laps['TeamName'] == team) & (clean_laps['Compound'] == compound)]
            subset = subset.dropna(subset=['TyreLife', 'FullyCorrected_LapTimeSeconds'])
            
            if len(subset) > 10:
                model = LinearRegression()
                X = subset[['TyreLife']]; y = subset['FullyCorrected_LapTimeSeconds']
                model.fit(X, y) 
                deg_rate_sec_per_lap = model.coef_[0]
                
                deg_data.append({
                    'TeamName': team, 'Compound': compound,
                    'DegRate_sec_lap': deg_rate_sec_per_lap, 'LapsAnalyzed': len(subset)
                })

    deg_df = pd.DataFrame(deg_data)
    compound_order = ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']
    compound_dtype = pd.CategoricalDtype(categories=compound_order, ordered=True)
    deg_df['Compound'] = deg_df['Compound'].astype(compound_dtype)
    deg_df = deg_df.sort_values(by=['TeamName', 'Compound'])
    
    return deg_df

# --- タブの定義 ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Session Analysis (セッション分析)", 
    "📈 Advanced Degradation (高度な劣化分析)",
    "🗺️ Pit Strategy (ピット戦略)",
    "⚔️ H2H Pace Comparison (H2H)"
])


# --- タブ1 (セッション分析) ---
with tab1:
    st.header(f"{selected_year} {selected_race} - {selected_session}")
    if laps is None or laps.empty:
        st.info("サイドバーで分析したい「年」「レース」「セッション」を選択してください。")
    
    # 予選・練習走行
    elif selected_session in ['Qualifying', 'Sprint Shootout', 'Q', 'SQ', 'Practice 1', 'Practice 2', 'Practice 3', 'FP1', 'FP2', 'FP3']:
        st.info(f"{selected_session}セッションです。全ドライバーの最速ラップを表示します。")
        try:
            # (Qxハイライトロジックは煩雑なため、シンプルな最速ラップ表示に戻します)
            fastest_laps = laps.pick_fastest()
            fastest_laps_summary = fastest_laps[['Driver', 'LapTime', 'Compound', 'TyreLife', 'Stint']]
            st.dataframe(fastest_laps_summary.set_index('Driver').sort_values('LapTime'), use_container_width=True)
        except Exception as e:
            st.error(f"最速ラップの分析中にエラーが発生しました: {e}")

    # 決勝・スプリント
    elif selected_session in ['Race', 'Sprint', 'S', 'R']:
        st.info("決勝/スプリントセッションです。ドライバーのラップタイムを分析します。")
        laps_cleaned = laps.pick_accurate() 
        if laps_cleaned.empty:
            st.warning("分析可能なクリーンラップデータがありません。")
        else:
            laps_cleaned['LapTimeSeconds'] = laps_cleaned['LapTime'].dt.total_seconds()
            drivers = laps_cleaned['Driver'].unique(); drivers.sort()
            default_driver = 'TSU' if 'TSU' in drivers else drivers[0]
            selected_driver = st.sidebar.selectbox("Select Driver (for Tab 1):", drivers, index=list(drivers).index(default_driver))
            st.subheader(f"{selected_driver} Lap Time Analysis")
            driver_laps_final = laps_cleaned.pick_driver(selected_driver)
            
            if not driver_laps_final.empty:
                fig_driver = px.scatter(driver_laps_final, x='LapNumber', y='LapTimeSeconds', color='Compound',
                                     color_discrete_map=TYRE_COLORS, hover_data=['Stint', 'TyreLife'])
                fig_driver.update_layout(title=f"{selected_driver} - Lap Times by Lap Number", xaxis_title="Lap Number", yaxis_title="Lap Time (Seconds)")
                st.plotly_chart(fig_driver, use_container_width=True)
            else: st.warning(f"選択された {selected_driver} のラップデータが見つかりませんでした。")


# --- タブ2 (高度な劣化分析) ---
with tab2:
    st.header("📈 Advanced Tyre Degradation Analysis")
    if laps is None or results is None or selected_session not in ['Race', 'Sprint', 'S', 'R']:
        st.info("この分析は、「決勝(Race)」または「スプリント(Sprint)」セッション選択時のみ利用可能です。")
    else:
        st.markdown("""
        **F1ストラテジスト手法:** 燃料負荷と路面進化のバイアスを補正し、チーム/コンパウンドごとの**真のデグラデーション率**（1周あたり何秒遅くなるか）を線形回帰で計算します。
        """)
        
        # ★★★ 修正点1: 実行ボタンの追加 ★★★
        if st.button("Run Advanced Degradation Analysis"):
            with st.spinner("高度な補正と回帰モデルを実行中..."):
                try:
                    # ★★★ 修正点2: キャッシュなしで直接関数を呼び出す ★★★
                    # (UnhashableTypeErrorを避けるため、ここでは@st.cache_dataを使用しない)
                    deg_df = calculate_advanced_deg(laps, results)
                    
                    if deg_df.empty:
                         st.warning("分析に必要な最低周回数（10周）を満たすクリーンラップがありませんでした。")
                    else:
                        compound_order = ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']
                        fig_deg_bar = px.bar(
                            deg_df, x='TeamName', y='DegRate_sec_lap', color='Compound', barmode='group',
                            color_discrete_map=TYRE_COLORS, category_orders={'Compound': compound_order},
                            title=f"{selected_race} - Calculated Tyre Degradation Rate",
                            labels={'DegRate_sec_lap': 'Degradation Rate (seconds per lap)', 'TeamName': 'Team'}
                        )
                        st.plotly_chart(fig_deg_bar, use_container_width=True)
                        st.subheader("Raw Data")
                        st.dataframe(deg_df.round(4).set_index(['TeamName', 'Compound']))
                except Exception as e:
                    st.error(f"分析の実行中にエラーが発生しました: {e}")
                    st.error("Trace: " + str(e))
        else:
            st.info("分析を実行するには、上のボタンを押してください。")


# --- タブ3 (ピット戦略 - 変更なし) ---
with tab3:
    st.header("🗺️ Pit Strategy Timeline (Gantt Chart)")
    if laps is None or results is None or selected_session not in ['Race', 'Sprint', 'S', 'R']:
        st.info("この分析は、「決勝(Race)」または「スプリント(Sprint)」セッション選択時のみ利用可能です。")
    else:
        try:
            stints_df = laps.groupby(['Driver', 'Stint']).agg(
                Lap_Start=('LapNumber', 'min'), Lap_End=('LapNumber', 'max'), Compound=('Compound', 'first')    
            ).reset_index()
            stints_df['Stint_Length'] = stints_df['Lap_End'] - stints_df['Lap_Start'] + 1
            drivers_list_sorted = results['Abbreviation'].tolist() 
            fig_timeline = px.bar(
                stints_df, base="Lap_Start", x="Stint_Length", y="Driver", color="Compound",       
                color_discrete_map=TYRE_COLORS, orientation='h', hover_data=['Stint', 'Lap_Start', 'Lap_End']
            )
            fig_timeline.update_yaxes(categoryorder='array', categoryarray=list(reversed(drivers_list_sorted)))
            fig_timeline.update_layout(title=f"{selected_race} - Race Pit Stop Strategy", xaxis_title="Lap Number")
            st.plotly_chart(fig_timeline, use_container_width=True)
        except Exception as e:
            st.error(f"ガントチャートの描画中にエラーが発生しました: {e}")


# --- タブ4 (H2H ペース比較 - 変更なし) ---
with tab4:
    st.header("⚔️ Head-to-Head (H2H) Pace Comparison")
    
    if laps is None or selected_session not in ['Race', 'Sprint', 'S', 'R']:
        st.info("この分析は、「決勝(Race)」または「スプリント(Sprint)」セッション選択時のみ利用可能です。")
    else:
        laps_cleaned = laps.pick_accurate()
        if laps_cleaned.empty:
            st.warning("比較対象のクリーンラップデータがありません。")
        else:
            laps_cleaned['LapTimeSeconds'] = laps_cleaned['LapTime'].dt.total_seconds()
            drivers_list = laps_cleaned['Driver'].unique(); drivers_list.sort()
            
            st.sidebar.subheader("H2H Driver Selection (Tab 4)")
            driver1_index = list(drivers_list).index('TSU') if 'TSU' in drivers_list else 0
            driver1 = st.sidebar.selectbox("Select Driver 1:", drivers_list, index=driver1_index)
            driver2_index = list(drivers_list).index('RIC') if 'RIC' in drivers_list and driver1 != 'RIC' else (driver1_index + 1) % len(drivers_list) if len(drivers_list) > 1 else 0
            driver2 = st.sidebar.selectbox("Select Driver 2:", drivers_list, index=driver2_index)
            
            if driver1 == driver2: st.warning("比較のために、異なる2人のドライバーを選択してください。")
            else:
                laps_d1 = laps_cleaned.pick_driver(driver1)[['LapNumber', 'LapTimeSeconds']]
                laps_d2 = laps_cleaned.pick_driver(driver2)[['LapNumber', 'LapTimeSeconds']]
                h2h_data = pd.merge(laps_d1, laps_d2, on='LapNumber', suffixes=(f'_{driver1}', f'_{driver2}'))
                
                if h2h_data.empty: st.warning(f"{driver1} と {driver2} の間に、比較可能なクリーンラップが1周もありませんでした。")
                else:
                    h2h_data['Delta'] = h2h_data[f'LapTimeSeconds_{driver1}'] - h2h_data[f'LapTimeSeconds_{driver2}']
                    st.subheader(f"Pace Comparison: {driver1} vs {driver2}")

                    h2h_melted = h2h_data.melt(id_vars=['LapNumber'], value_vars=[f'LapTimeSeconds_{driver1}', f'LapTimeSeconds_{driver2}'], var_name='Driver', value_name='LapTime')
                    h2h_melted['Driver'] = h2h_melted['Driver'].str.replace('LapTimeSeconds_', '')
                    
                    fig_h2h_laps = px.line(h2h_melted, x='LapNumber', y='LapTime', color='Driver', title=f"Lap Times: {driver1} vs {driver2}")
                    st.plotly_chart(fig_h2h_laps, use_container_width=True)

                    st.subheader(f"Time Delta per Lap ({driver1} vs {driver2})")
                    st.info(f"プラス ( > 0 ) の場合: {driver1} が {driver2} より遅い\n\nマイナス ( < 0 ) の場合: {driver1} が {driver2} より速い")
                    
                    fig_h2h_delta = px.area(h2h_data, x='LapNumber', y='Delta', title=f"Delta: {driver1} (Time) - {driver2} (Time)")
                    fig_h2h_delta.add_hline(y=0, line_dash="dash", line_color="black")
                    st.plotly_chart(fig_h2h_delta, use_container_width=True)