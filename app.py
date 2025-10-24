import streamlit as st
import fastf1 as ff1
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

st.title("F1 Data Analysis Dashboard")
st.header("Driver Lap Time Analysis") 

@st.cache_data
def load_session_data(year, race, session_type):
    try:
        session = ff1.get_session(year, race, session_type)
        session.load()
        laps = session.laps
        return laps
    except Exception as e:
        st.warning(f"データ取得エラー: {e}")
        return None 

laps = load_session_data(2024, 4, 'R') 

if laps is not None:
    drivers = laps['Driver'].unique()
    drivers.sort()

    st.sidebar.header("Filter Options")
    
    default_index = list(drivers).index('TSU') if 'TSU' in drivers else 0
    selected_driver = st.sidebar.selectbox(
        "Select Driver:", 
        drivers, 
        index=default_index
    )

    st.subheader(f"{selected_driver} - Lap Time Analysis (Suzuka 2024)")

    driver_laps = laps.pick_driver(selected_driver)

    driver_laps['LapTimeSeconds'] = driver_laps['LapTime'].dt.total_seconds()

    driver_laps_cleaned = driver_laps.loc[driver_laps['LapTimeSeconds'] < 110]

    if driver_laps_cleaned.empty:
        st.warning(f"{selected_driver} has no valid lap data for this analysis.")
    else:
        fig = px.scatter(driver_laps_cleaned, 
                         x='LapNumber',
                         y='LapTimeSeconds',
                         color='Compound',
                         hover_data=['Stint', 'TyreLife'])

        fig.update_layout(title=f"{selected_driver} - Lap Time Analysis (Suzuka 2024)",
                          xaxis_title="Lap Number",
                          yaxis_title="Lap Time (Seconds)")

        st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Failed to load session data.")
    st.info("FastF1 data source might be unavailable. Please check ./cache folder or try again later.")