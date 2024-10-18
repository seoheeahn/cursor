from flask import Flask, render_template, request, jsonify, session
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from functools import lru_cache
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션을 위한 비밀 키 설정

# 캐시 유효 시간 (초)
CACHE_EXPIRATION = 300  # 5분

def calculate_technical_indicators(df):
    try:
        # 이동평균선 계산
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        
        # MACD 계산
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['Signal']
        
        # RSI 계산
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df
    except Exception as e:
        print(f"Error in calculate_technical_indicators: {str(e)}")
        return df

@lru_cache(maxsize=100)
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        
        # 주가 데이터 가져오기 (1년)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        data = stock.history(start=start_date, end=end_date)
        
        # 데이터가 비어있는지 확인
        if data.empty:
            print(f"No data returned for symbol: {symbol}")
            return None
        
        # 기술적 지표 계산
        data = calculate_technical_indicators(data)
        
        # 주식 정보 가져오기
        info = stock.info
        
        # 데이터 확인
        print(data.head())  # 데이터의 첫 몇 행을 출력
        
        price_data = data['Close'].tolist()
        volume_data = data['Volume'].tolist()
        dates = [d.strftime('%Y-%m-%d') for d in data.index]  # 날짜를 문자열로 변환
        
        # 재무 데이터 가져오기
        income_statement = {
            'Total Revenue': info.get('totalRevenue', 'N/A'),
            'Gross Margins': info.get('grossMargins', 'N/A'),
            'EBITDA': info.get('ebitda', 'N/A'),
            'Operating Margins': info.get('operatingMargins', 'N/A'),
            'Profit Margins': info.get('profitMargins', 'N/A'),
        }
        
        balance_sheet = {
            'Market Cap': info.get('marketCap', 'N/A'),
            'Enterprise Value': info.get('enterpriseValue', 'N/A'),
            'Total Debt': info.get('totalDebt', 'N/A'),
            'Total Cash': info.get('totalCash', 'N/A'),
            'Debt to Equity': info.get('debtToEquity', 'N/A'),
            'Current Ratio': info.get('currentRatio', 'N/A'),
        }
        
        # 뉴스 가져오기
        news = stock.news[:5]
        
        return {
            'dates': dates,
            'price': price_data,
            'open': data['Open'].tolist(),
            'high': data['High'].tolist(),
            'low': data['Low'].tolist(),
            'volume': volume_data,
            'sma50': data['SMA50'].tolist(),
            'sma200': data['SMA200'].tolist(),
            'macd': data['MACD'].tolist(),
            'signal': data['Signal'].tolist(),
            'macd_histogram': data['MACD_Histogram'].tolist(),
            'rsi': data['RSI'].tolist(),
            'income_statement': income_statement,
            'balance_sheet': balance_sheet,
            'news': news,
            'info': info
        }
    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        return None

@app.route('/')
def index():
    if 'history' not in session:
        session['history'] = []
    return render_template('index.html', history=session['history'])

@app.route('/get_data', methods=['POST'])
def get_data():
    try:
        # 사용자가 입력한 심볼을 가져옵니다.
        symbol = request.form.get('symbol', '').strip()  # 입력값을 가져오고 공백 제거
        
        # 심볼이 비어있으면 기본값으로 'MSFT' 사용
        if not symbol:
            symbol = 'MSFT'
        
        if symbol not in session['history']:
            session['history'].append(symbol)
            session.modified = True
        
        result = get_stock_data(symbol)
        
        if result is None:
            print(f"No data returned for symbol: {symbol}")
            return jsonify({'error': f'데이터를 가져오는 데 실패했습니다. Symbol: {symbol}'}), 400
        
        print(f"Data successfully fetched for symbol: {symbol}")
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_data: {str(e)}")
        return jsonify({'error': f'서버 오류가 발생했습니다: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)