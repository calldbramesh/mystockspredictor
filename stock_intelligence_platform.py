
import streamlit as st
import sqlite3
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="Stock Intelligence Platform", layout="wide")

DB = sqlite3.connect("stock_platform.db", check_same_thread=False)

def load_data(ticker, period="1y"):

    df = yf.download(
        ticker,
        period=period,
        auto_adjust=True,
        progress=False
    )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.reset_index(inplace=True)

    return df

def indicators(df):

    close = pd.Series(df["Close"]).astype(float)

    df["SMA20"] = close.rolling(20).mean()

    df["EMA20"] = close.ewm(
        span=20,
        adjust=False
    ).mean()

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    rs = (
        gain.rolling(14).mean()
        /
        loss.rolling(14).mean()
    )

    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = close.ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False
    ).mean()

    df["MACD"] = ema12 - ema26

    df["Signal"] = df["MACD"].ewm(
        span=9,
        adjust=False
    ).mean()

    rolling_std = close.rolling(20).std()

    df["BB_UPPER"] = (
        df["SMA20"] + 2 * rolling_std
    )

    df["BB_LOWER"] = (
        df["SMA20"] - 2 * rolling_std
    )

    return df

def predict_price(df):

    d = df.dropna().copy()

    d["Day"] = np.arange(len(d))

    X = d[["Day"]]
    y = d["Close"]

    model = LinearRegression()

    model.fit(X, y)

    future = pd.DataFrame(
        {"Day": [len(d) + 30]}
    )

    return float(
        model.predict(future)[0]
    )

WATCHLIST = [
    "BEL.NS",
    "SUZLON.NS",
    "VEDL.NS",
    "VBL.NS",
    "AVANTEL.NS",
    "TATAPOWER.NS",
    "GOLDBEES.NS",
    "NIFTYBEES.NS"
]

st.title("📈 AI Stock Intelligence Platform")

ticker = st.sidebar.text_input(
    "Ticker",
    "BEL.NS"
)
period = st.sidebar.selectbox("Period", ["6mo","1y","2y","5y"])

df = load_data(ticker, period)
if "Close" not in df.columns:
    st.error("Invalid ticker")
    st.stop()
 
df = indicators(df)
df.to_sql(ticker, DB, if_exists="replace", index=False)

prediction = predict_price(df)
current = float(df["Close"].iloc[-1])

tab1, tab2, tab3, tab4 = st.tabs(
    ["Overview","Technical","Prediction","Database"]
)

with tab1:
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Current", f"${current:.2f}")
    c2.metric("Predicted 30D", f"${prediction:.2f}")
    c3.metric("RSI", f"{df['RSI'].iloc[-1]:.2f}")
    c4.metric("Volume", f"{int(df['Volume'].iloc[-1]):,}")

    fig = go.Figure(data=[go.Candlestick(
        x=df["Date"],
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"]
    )])
    st.plotly_chart(
    fig,
    width="stretch"
)
st.plotly_chart(
    fig,
    width="stretch",
    key="candlestick_chart"  
)

with tab2:
    fig2 = go.Figure()
    fig2.add_scatter(x=df["Date"], y=df["Close"], name="Close")
    fig2.add_scatter(x=df["Date"], y=df["SMA20"], name="SMA20")
    fig2.add_scatter(x=df["Date"], y=df["EMA20"], name="EMA20")
    fig2.add_scatter(x=df["Date"], y=df["BB_UPPER"], name="BB Upper")
    fig2.add_scatter(x=df["Date"], y=df["BB_LOWER"], name="BB Lower")
    st.plotly_chart(
    fig2,
    width="stretch",
    key="technical_chart"
    )

    st.line_chart(df.set_index("Date")[["RSI"]])
    st.line_chart(df.set_index("Date")[["MACD","Signal"]])

with tab3:
    change = ((prediction-current)/current)*100
    st.metric("Expected Return %", f"{change:.2f}%")

    if change > 10:
        st.success("Bullish outlook")
    elif change < -10:
        st.error("Bearish outlook")
    else:
        st.info("Neutral outlook")

with tab4:
    st.dataframe(
    df,
    width="stretch"
)

st.caption("Single-file Stock Intelligence Platform")
