import streamlit as st
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd

# --- 1. 데이터 수집 함수 ---
@st.cache_data(ttl=600) # 10분 동안 데이터 임시 저장(속도 향상)
def get_market_data():
    # 1. 환율 가져오기 (네이버)
    url = "https://finance.naver.com/marketindex/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    rate_text = soup.select_one("a.head.usd span.value").text
    exchange_rate = float(rate_text.replace(',', ''))
    
    # 2. JEPQ 실시간 주가 및 배당금 가져오기 (야후 파이낸스)
    jepq = yf.Ticker("JEPQ")
    
    # 현재 주가
    current_price = jepq.history(period="1d")['Close'].iloc[-1]
    
    # 최근 1년(TTM) 누적 배당금 계산
    divs = jepq.dividends
    one_year_ago = pd.Timestamp.now(tz=divs.index.tz) - pd.DateOffset(years=1)
    ttm_div_per_share = divs[divs.index >= one_year_ago].sum()
    
    # 연 배당률(%) 계산
    dividend_yield = (ttm_div_per_share / current_price) * 100
    
    return exchange_rate, float(current_price), float(ttm_div_per_share), float(dividend_yield)

# --- 2. 배당금 계산 로직 (세전/세후 분리) ---
def calc_dividend_income(investment_krw, exchange_rate, price_dollar, ttm_div_per_share):
    # 매수 가능 주식 수 (소수점 버림 처리)
    investment_dollar = investment_krw / exchange_rate
    shares = int(investment_dollar // price_dollar) 
    
    # 세전 배당금 (Pre-tax)
    annual_pre_usd = shares * ttm_div_per_share
    annual_pre_krw = annual_pre_usd * exchange_rate
    
    # 세후 배당금 (Post-tax, 미국 배당소득세 15% 공제)
    TAX_RATE = 0.15
    annual_post_usd = annual_pre_usd * (1 - TAX_RATE)
    annual_post_krw = annual_post_usd * exchange_rate
    
    return {
        "shares": shares,
        "annual_pre": annual_pre_krw,
        "monthly_pre": annual_pre_krw / 12,
        "annual_post": annual_post_krw,
        "monthly_post": annual_post_krw / 12
    }

# --- 3. 웹사이트 화면 구성 ---
st.set_page_config(page_title="JEPQ 전문 계산기", page_icon="📈", layout="centered")

st.title("📈 JEPQ 실시간 배당 시뮬레이터")
st.markdown("실시간 주가 및 최근 1년 배당 내역을 바탕으로 **세전/세후 현금흐름**을 계산합니다.")
st.markdown("---")

# 실시간 데이터 로딩
with st.spinner("글로벌 금융 데이터를 동기화하는 중입니다..."):
    ex_rate, jepq_price, ttm_div, div_yield = get_market_data()

# 현재 시장 데이터 요약 박스
st.success("✅ 실시간 시장 데이터 동기화 완료")
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("현재 환율", f"{ex_rate:,.2f}원")
col_m2.metric("JEPQ 실시간 주가", f"${jepq_price:,.2f}")
col_m3.metric("최근 1년 배당률", f"{div_yield:.2f}%", f"주당 ${ttm_div:,.2f}")

st.markdown("---")

# 사용자 입력창
investment_krw = st.number_input(
    "💰 투자하실 금액(원)을 입력해주세요:", 
    min_value=0, 
    value=100000000, 
    step=10000000
)

# 계산 버튼
if st.button("전문 분석 결과 보기 🚀", type="primary"):
    result = calc_dividend_income(investment_krw, ex_rate, jepq_price, ttm_div)
    
    st.subheader(f"🛒 매수 가능 주식 수: {result['shares']:,}주")
    
    # 세전 / 세후 비교 탭(Tab) 만들기
    tab1, tab2 = st.tabs(["🟢 세후 (Post-Tax) - 실제 수령액", "🟡 세전 (Pre-Tax) - 명목 금액"])
    
    with tab1:
        st.info("※ 미국 배당소득세 15% 공제 후 실제 입금되는 금액입니다.")
        c1, c2 = st.columns(2)
        c1.metric(label="예상 월 수령액", value=f"{int(result['monthly_post']):,}원")
        c2.metric(label="예상 연 수령액", value=f"{int(result['annual_post']):,}원")
        
    with tab2:
        st.warning("※ 세금 공제 전 명목 배당금액입니다.")
        c3, c4 = st.columns(2)
        c3.metric(label="명목 월 배당금", value=f"{int(result['monthly_pre']):,}원")
        c4.metric(label="명목 연 배당금", value=f"{int(result['annual_pre']):,}원")