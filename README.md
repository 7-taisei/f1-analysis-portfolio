# F1 Data-Analysis & Prediction Dashboard

## Overview
This project is a web application that analyzes historical Formula 1 race data, visualizes strategies and performance, and attempts to predict race outcomes using machine learning.

## Motivation
- To gain a deeper understanding of my hobby, watching Formula 1, through the power of data science.
- Apply the data analysis and machine learning skills learned at university to practical projects and publish them as a portfolio.

## technologies - Planned
- **Data Acquisition:** `FastF1` (Python library)
- **Data Processing & Analysis:** `Python`, `Pandas`, `NumPy`
- **Data Visualization:** `Plotly` (interactive graphs)
- **Machine Learning Models:** `Scikit-learn`
- **Web Applications:** `Streamlit`
- **Environment & Version Control:** `Git`, `GitHub`, `VS Code`

## Features & Analysis Themes
We aim to implement the following features and analytical themes that allow F1 fans to deep dive into the excitement of the race through data.
### Core Analysis
- **Race Strategy Analysis:**
    - Visualization of degradation (performance deterioration) by tire compound.
    - Analysis of pit stop strategy (undercut/overcut) effectiveness via gap fluctuations.
- **Driver Performance Analysis:**
    - Comparison of lap time trends between drivers and pace per stint (tire change interval).
    - (WIP) Comparison of driver inputs at specific corners using telemetry data (speed, throttle, brakes).

### Interactive Features
- **Personalized Analysis:**
    - A feature that displays analysis graphs focused on the user's selected favorite teams or drivers.

## Future Work
- **Machine Learning (ML) Model Implementation:**
    - Build a model predicting race finish positions using qualifying results, tire strategy, and historical performance data as features.
- **Advanced Simulation and Analysis:**
    -   Perform simplified simulations of optimal pit stop timing based on in-race data (tire age, fuel).
- **Immersive Experience (Historical Comparison):**
    -   Load data from years with different regulations (e.g., 2021 vs. 2022) to compare and analyze performance and strategy differences.