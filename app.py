from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

app = Flask(__name__)

search_history = []

def calculate_macd(data, short_window=12, long_window=26, signal_window=9):
    short_ema = data.ewm(span=short_window, adjust=False).mean()
    long_ema = data.ewm(span=long_window, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=signal_window, adjust=False).mean()
    histogram = macd - signal
    return macd, signal, histogram

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.interpolate(method='linear').fillna(method='bfill')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        symbol = request.form['symbol']
        period = request.form.get('period', '2y')  # 기본값 2년
        
        if symbol not in search_history:
            search_history.append(symbol)
        
        end_date = datetime.now()
        
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        
        # RSI 계산
        rsi = calculate_rsi(hist['Close'])
        
        # MACD 계산
        macd, signal, histogram = calculate_macd(hist['Close'])
        
        # 50일 이동평균 계산
        ma50 = hist['Close'].rolling(window=50).mean()
        
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.05, 
                            subplot_titles=('주가', '거래량', 'RSI', 'MACD'),
                            row_heights=[0.4, 0.2, 0.2, 0.2])
        
        # 주가 차트
        fig.add_trace(go.Candlestick(x=hist.index,
                                     open=hist['Open'],
                                     high=hist['High'],
                                     low=hist['Low'],
                                     close=hist['Close'],
                                     name='주가'),
                      row=1, col=1)
        
        # 50일 이동평균선 추가
        fig.add_trace(go.Scatter(x=hist.index, y=ma50, name='MA50', line=dict(color='red', width=1)), row=1, col=1)
        
        # 거래량 차트
        fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name='거래량'), row=2, col=1)
        
        # RSI 차트
        fig.add_trace(go.Scatter(x=hist.index, y=rsi, name='RSI', line=dict(color='purple')), row=3, col=1)
        
        # MACD 차트
        fig.add_trace(go.Scatter(x=hist.index, y=macd, name='MACD', line=dict(color='blue')), row=4, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=signal, name='Signal', line=dict(color='orange')), row=4, col=1)
        fig.add_trace(go.Bar(x=hist.index, y=histogram, name='Histogram', marker_color='gray'), row=4, col=1)
        
        # 차트 레이아웃 설정
        fig.update_layout(
            height=1000, 
            title_text=f"{symbol} 주가 분석", 
            xaxis_rangeslider_visible=False,
            plot_bgcolor='white', 
            paper_bgcolor='white'
        )
        
        # X축 설정 (날짜 범위 표시)
        fig.update_xaxes(
            rangebreaks=[dict(bounds=["sat", "mon"])],  # 주말 제외
            tickformat="%Y-%m-%d",
            tickangle=45,
            tickmode='auto',
            nticks=10,
            row=4, col=1
        )
        
        fig.update_yaxes(title_text="가격", row=1, col=1, autorange=True)
        fig.update_yaxes(title_text="거래량", row=2, col=1)
        fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)
        fig.update_yaxes(title_text="MACD", row=4, col=1)
        
        chart = fig.to_html(full_html=False, config={'responsive': True})
        
        # 재무 데이터 가져오기
        info = stock.info
        financials = stock.financials
        
        financial_data = {
            "Total Revenue": financials.loc["Total Revenue"].iloc[0] if "Total Revenue" in financials.index else 'N/A',
            "Gross Profit": financials.loc["Gross Profit"].iloc[0] if "Gross Profit" in financials.index else 'N/A',
            "Net Income": financials.loc["Net Income"].iloc[0] if "Net Income" in financials.index else 'N/A',
            "Debt to Equity": info.get('debtToEquity', 'N/A'),
            "EBITDA": financials.loc["EBITDA"].iloc[0] if "EBITDA" in financials.index else info.get('ebitda', 'N/A'),
            "ROE": info.get('returnOnEquity', 'N/A'),
            "ROA": info.get('returnOnAssets', 'N/A')
        }
        
        financial_date = financials.columns[0].strftime('%Y-%m-%d') if not financials.empty else 'N/A'
        
        return render_template('index.html', chart=chart, symbol=symbol, search_history=search_history,
                               financial_data=financial_data, financial_date=financial_date)
    
    return render_template('index.html', search_history=search_history)

if __name__ == '__main__':
    app.run(debug=True)
