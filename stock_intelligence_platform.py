
import streamlit as st
import sqlite3
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from textblob import TextBlob
import feedparser
from sklearn.ensemble import RandomForestClassifier
from twilio.rest import Client
universe = pd.read_csv("stocks200.csv")

ALL_STOCKS = (
    universe["ticker"]
    .dropna()
    .unique()
    .tolist()
)

st.set_page_config(page_title="Stock Intelligence Platform", layout="wide")

DB = sqlite3.connect("stock_platform.db", check_same_thread=False)

cursor = DB.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS portfolio(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT,
    quantity INTEGER,
    buy_price REAL
)
""")

DB.commit()


@st.cache_data(ttl=60)
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

   
def get_news_sentiment(stock):

    query = stock.replace(".NS", "")

    url = f"https://news.google.com/rss/search?q={query}"

    feed = feedparser.parse(url)

    sentiments = []
    headlines = []

    for entry in feed.entries[:10]:

        title = entry.title

        score = TextBlob(
            title
        ).sentiment.polarity

        sentiments.append(score)

        headlines.append({
            "headline": title,
            "sentiment": round(score,3)
        })

    avg_sentiment = (
        sum(sentiments)/len(sentiments)
        if sentiments else 0
    )

    return avg_sentiment, headlines

def risk_metrics(df):

    returns = (
        df["Close"]
        .pct_change()
        .dropna()
    )

    volatility = (
        returns.std()
        * np.sqrt(252)
    )

    sharpe = (
        returns.mean()
        /
        returns.std()
    ) * np.sqrt(252)

    cumulative = (
        1 + returns
    ).cumprod()

    drawdown = (
        cumulative
        /
        cumulative.cummax()
    ) - 1

    max_drawdown = (
        drawdown.min()
    )

    return (
        volatility,
        sharpe,
        max_drawdown
    )

ALL_STOCKS = (
    universe["ticker"]
    .dropna()
    .tolist()
)

st.title("📈 AI Stock Intelligence Platform")




def predict_price(df):

    d = df.dropna().copy()

    d["Day"] = np.arange(len(d))

    X = d[["Day"]]

    y = d["Close"]

    model = LinearRegression()

    model.fit(X, y)

    future = pd.DataFrame(
        {"Day":[len(d)+30]}
    )

    return float(
        model.predict(future)[0]
    )


def generate_signal(df):

    data = df.copy()

    data["Future"] = (
        data["Close"].shift(-5)
        >
        data["Close"]
    ).astype(int)

    data = data[
        [
            "RSI",
            "MACD",
            "Signal",
            "Future"
        ]
    ].dropna()

    if len(data) < 50:
        return 0, 0

    X = data[
        [
            "RSI",
            "MACD",
            "Signal"
        ]
    ]

    y = data["Future"]

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42
    )

    model.fit(X, y)

    latest = X.iloc[-1:]

    prediction = model.predict(latest)[0]
    current = float(
    df["Close"].iloc[-1]
    
)
    confidence = (
        model.predict_proba(latest)[0].max()
    )

    return prediction, confidence
    
def ai_rank_stock(stock):

    try:

        temp = load_data(
            stock,
            "1y"
        )

        temp = indicators(temp)

        current = float(
            temp["Close"].iloc[-1]
        )

        prediction = predict_price(temp)

        expected_return = (
            (prediction-current)
            / current
        ) * 100

        score = 50

        if temp["RSI"].iloc[-1] < 40:
            score += 15

        if (
            temp["MACD"].iloc[-1]
            >
            temp["Signal"].iloc[-1]
        ):
            score += 15

        if expected_return > 5:
            score += 20

        if expected_return > 10:
            score += 10
        vol, sharpe, mdd = risk_metrics(temp)

        if sharpe > 1:
            score += 10

        if mdd > -0.20:
            score += 5

        return {
            "Stock": stock,
            "Price": round(current,2),
            "Expected Return %":
                round(expected_return,2),
            "AI Score":
                min(score,100)
        }

    except:

        return None
if st.sidebar.button("🔄 Refresh Data"):
if st.button("📲 Send Top Pick"):

    best = rank_df.iloc[0]

    msg = f"""
🏆 Top Pick

    st.cache_data.clear()
    st.rerun()
    
scanner_size = st.sidebar.selectbox(
    "Scanner Size",
    [25, 50, 100, 200],
    index=2,
    key="scanner_size"
)

ticker = st.sidebar.selectbox(
    "Select Stock",
    ALL_STOCKS,
    key="ticker_selector"
)

period = st.sidebar.selectbox(
    "Period",
    ["6mo", "1y", "2y", "5y"],
    key="period_selector"
)

stocks_to_scan = ALL_STOCKS[:scanner_size]


df = load_data(ticker, period)
if "Close" not in df.columns:
    st.error("Invalid ticker")
    st.stop()
 
df = indicators(df)
df.to_sql(ticker, DB, if_exists="replace", index=False)

prediction = predict_price(df)

current = float(
    df["Close"].iloc[-1]
)

change = (
    (prediction-current)
    / current
) * 100

rf_signal, rf_confidence = generate_signal(df)

vol, sharpe, mdd = risk_metrics(df)

sentiment, headlines = get_news_sentiment(ticker)

technical_score = 50

if rf_signal == 1:
    technical_score += 20

if prediction > current:
    technical_score += 15

if df["MACD"].iloc[-1] > df["Signal"].iloc[-1]:
    technical_score += 10

if df["RSI"].iloc[-1] < 40:
    technical_score += 10

if sentiment > 0:
    technical_score += 10

ai_score = max(
    0,
    min(100, technical_score)
)   


tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(
[
    "Overview",
    "Technical",
    "Prediction",
    "AI Signal",
    "News",
    "Risk",
    "Portfolio",
    "Database",
    "Top Picks"
]
)

with tab1:
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Current", f"₹{current:.2f}")
    c2.metric("Predicted 30D", f"₹{prediction:.2f}")
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

    st.metric(
        "Confidence",
        f"{rf_confidence*100:.1f}%"
    )

    if rf_signal == 1:

        st.success(
            "BUY Signal"
        )

    else:

        st.error(
            "SELL Signal"
        )

    st.metric(
        "AI Score",
        ai_score
    )

with tab5:

    st.metric(
        "Sentiment",
        round(sentiment,3)
    )

    for item in headlines:

        st.write(
            f"{item['sentiment']} | "
            f"{item['headline']}"
        )

with tab6:

    c1,c2,c3 = st.columns(3)

    c1.metric(
        "Volatility",
        f"{vol:.2f}"
    )

    c2.metric(
        "Sharpe",
        f"{sharpe:.2f}"
    )

    c3.metric(
        "Max Drawdown",
        f"{mdd:.2%}"
    )

with tab7:

    qty = st.number_input(
        "Quantity",
        min_value=1,
        value=1
    )

    buy_price = st.number_input(
        "Buy Price",
        value=float(current)
    )

    if st.button(
        "Add Position"
    ):

        cursor.execute(
        """
        INSERT INTO portfolio(
        ticker,
        quantity,
        buy_price
        )
        VALUES(?,?,?)
        """,
        (
            ticker,
            qty,
            buy_price
        )
        )

        DB.commit()

    portfolio_df = pd.read_sql(
        "SELECT * FROM portfolio",
        DB
    )

    st.dataframe(
        portfolio_df,
        width="stretch"
    )
with tab8:

    st.subheader("Stored Portfolio")

    portfolio_df = pd.read_sql(
        "SELECT * FROM portfolio",
        DB
    )

    st.dataframe(
        portfolio_df,
        width="stretch"
    )

    st.subheader("Latest Stock Data")

    st.dataframe(
        df.tail(50),
        width="stretch"
    )

with tab9:

    rankings = []

    progress = st.progress(0)

    total = len(stocks_to_scan)

    for i, stock in enumerate(stocks_to_scan):

        result = ai_rank_stock(stock)

        if result:
            rankings.append(result)

        progress.progress((i + 1) / total)

    rank_df = pd.DataFrame(rankings)

    if not rank_df.empty:

        rank_df = rank_df.sort_values(
            "AI Score",
            ascending=False
        )

        st.dataframe(
            rank_df,
            width="stretch"
        )

        best = rank_df.iloc[0]

        st.success(
            f"🏆 Best Pick: {best['Stock']}"
        )

        if st.button("📲 Send Top Pick"):

            msg = f"""
Top Pick

Stock: {best['Stock']}
AI Score: {best['AI Score']}
Expected Return: {best['Expected Return %']}%
"""

            send_whatsapp(msg)

            st.success("WhatsApp sent")

        if len(rank_df) >= 3:

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "🥇 Rank 1",
                rank_df.iloc[0]["Stock"]
            )

            c2.metric(
                "🥈 Rank 2",
                rank_df.iloc[1]["Stock"]
            )

            c3.metric(
                "🥉 Rank 3",
                rank_df.iloc[2]["Stock"]
            )

st.caption("Single-file Stock Intelligence Platform")
