import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime
import numpy as np
import os
import google.generativeai as genai

try:
    from dotenv import load_dotenv
    load_dotenv("c:/streamlit-project/.env")
except Exception:
    pass

api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
genai.configure(api_key=api_key)

st.set_page_config(page_title="IT 비용과 투자", layout="wide")

# 제목
st.title("📊 IT 비용과 투자 대시보드")
st.markdown("계정별 비용 현황 및 월별/연도별 추이 분석 (CSV 파일 기반)")

# ===== CSV 파일 로드 =====
@st.cache_data
def load_csv_data():
    """data 디렉토리의 모든 CSV 파일을 읽어서 병합"""
    data_dir = Path(__file__).parent / "data"

    all_data = []
    csv_files = sorted(data_dir.glob("cost_*.csv"))

    if not csv_files:
        st.error("❌ CSV 파일을 찾을 수 없습니다. data 디렉토리를 확인하세요.")
        return pd.DataFrame()

    for csv_file in csv_files:
        df = pd.read_csv(csv_file, encoding='utf-8')
        all_data.append(df)

    if not all_data:
        return pd.DataFrame()

    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df['날짜'] = pd.to_datetime(combined_df['날짜'])
    combined_df['연도'] = combined_df['날짜'].dt.year
    combined_df['월'] = combined_df['날짜'].dt.month

    return combined_df

# 데이터 로드
df = load_csv_data()

if df.empty:
    st.error("데이터를 로드할 수 없습니다.")
    st.stop()

# 데이터 통계
data_dir = Path(__file__).parent / "data"
st.sidebar.info(f"📁 로드된 파일: {len(list(data_dir.glob('*.csv')))}개\n📊 총 레코드: {len(df):,}개")

# ===== 사이드바 필터 =====
st.sidebar.header("🔍 필터")
selected_year = st.sidebar.multiselect(
    "연도 선택",
    sorted(df['연도'].unique()),
    default=sorted(df['연도'].unique())
)

selected_account = st.sidebar.multiselect(
    "계정 선택",
    sorted(df['계정'].unique()),
    default=sorted(df['계정'].unique())
)

# 데이터 필터링
filtered_df = df[
    (df['연도'].isin(selected_year)) &
    (df['계정'].isin(selected_account))
]

# ===== KPI 카드 =====
st.subheader("📈 주요 지표")
col1, col2, col3, col4 = st.columns(4)

total_cost = filtered_df['비용'].sum()
avg_cost = filtered_df['비용'].mean()
max_cost = filtered_df['비용'].max()
account_count = filtered_df['계정'].nunique()

with col1:
    st.metric("총 비용", f"₩{total_cost:,.0f}")

with col2:
    st.metric("평균 월간 비용", f"₩{avg_cost:,.0f}")

with col3:
    st.metric("최고 비용(월)", f"₩{max_cost:,.0f}")

with col4:
    st.metric("추적 중인 계정", f"{account_count}개")

st.divider()

# ===== 월별 추이 (선 그래프) =====
st.subheader("📅 월별 비용 추이")

# 날짜별로 계정별 비용을 집계
monthly_trend = filtered_df.groupby(['날짜', '계정'])['비용'].sum().reset_index()

fig_line = px.line(
    monthly_trend,
    x='날짜',
    y='비용',
    color='계정',
    markers=True,
    title="계정별 월별 비용 추이",
    labels={'비용': '비용 (₩)', '날짜': '날짜'},
    height=400
)

fig_line.update_layout(
    hovermode='x unified',
    yaxis_title='비용 (₩)',
    xaxis_title='날짜'
)

st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# ===== 연도별/계정별 비용 비교 =====
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 연도별 총 비용")
    yearly = filtered_df.groupby('연도')['비용'].sum().reset_index().sort_values('연도')

    fig_yearly = px.bar(
        yearly,
        x='연도',
        y='비용',
        title="연도별 총 비용",
        labels={'비용': '비용 (₩)', '연도': '연도'},
        height=350
    )

    fig_yearly.update_traces(marker_color='steelblue')
    st.plotly_chart(fig_yearly, use_container_width=True)

with col2:
    st.subheader("💰 계정별 총 비용")
    account_total = filtered_df.groupby('계정')['비용'].sum().reset_index().sort_values('비용', ascending=False)

    fig_account = px.bar(
        account_total,
        x='비용',
        y='계정',
        orientation='h',
        title="계정별 총 비용",
        labels={'비용': '비용 (₩)'},
        height=350
    )

    fig_account.update_traces(marker_color='coral')
    st.plotly_chart(fig_account, use_container_width=True)

st.divider()

# ===== 상세 데이터 테이블 =====
st.subheader("📋 상세 데이터")

# 테이블 타입 선택
table_type = st.radio("테이블 형식 선택", ["월별 피벗 (계정 × 월)", "원본 데이터"], horizontal=True)

if table_type == "월별 피벗 (계정 × 월)":
    # 월별 피벗 테이블
    pivot_table = filtered_df.pivot_table(
        values='비용',
        index='계정',
        columns='날짜',
        aggfunc='sum'
    ).round(2)

    # 열 이름을 yyyy-mm 형식으로 변환
    pivot_table.columns = pivot_table.columns.strftime('%Y-%m')

    # 합계 행 추가
    pivot_table['합계'] = pivot_table.sum(axis=1)

    st.dataframe(pivot_table, use_container_width=True)
else:
    # 원본 데이터 테이블
    display_df = filtered_df[['날짜', '계정', '비용', '연도', '월']].sort_values(['날짜', '계정'])
    display_df['비용'] = display_df['비용'].apply(lambda x: f"₩{x:,.2f}")

    st.dataframe(display_df, use_container_width=True)

st.divider()

# ===== 연도별 상세 분석 =====
st.subheader("🔎 연도별 상세 분석")

for year in sorted(selected_year):
    with st.expander(f"{year}년 분석"):
        year_df = filtered_df[filtered_df['연도'] == year]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(f"{year}년 총 비용", f"₩{year_df['비용'].sum():,.0f}")

        with col2:
            st.metric(f"{year}년 평균 월간 비용", f"₩{year_df['비용'].mean():,.0f}")

        with col3:
            year_ratio = (year_df['비용'].sum() / filtered_df['비용'].sum() * 100) if filtered_df['비용'].sum() > 0 else 0
            st.metric(f"{year}년 비용 비중", f"{year_ratio:.1f}%")

        # 해당 연도의 월별 데이터 표
        year_table = year_df.pivot_table(
            values='비용',
            index='계정',
            columns='월',
            aggfunc='sum'
        ).round(2)

        year_table.columns = [f"{int(col)}월" for col in year_table.columns]
        year_table['합계'] = year_table.sum(axis=1)

        st.dataframe(year_table, use_container_width=True)

st.divider()

# ===== 계정별 상세 분석 =====
st.subheader("💼 계정별 상세 분석")

for account in sorted(selected_account):
    with st.expander(f"{account}"):
        account_df = filtered_df[filtered_df['계정'] == account]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(f"{account} 총 비용", f"₩{account_df['비용'].sum():,.0f}")

        with col2:
            st.metric(f"{account} 평균", f"₩{account_df['비용'].mean():,.0f}")

        with col3:
            account_ratio = (account_df['비용'].sum() / filtered_df['비용'].sum() * 100) if filtered_df['비용'].sum() > 0 else 0
            st.metric(f"{account} 비중", f"{account_ratio:.1f}%")

        # 시계열 차트
        account_trend = account_df.sort_values('날짜')
        fig_account_trend = px.line(
            account_trend,
            x='날짜',
            y='비용',
            title=f"{account} 월별 추이",
            markers=True,
            height=250
        )
        st.plotly_chart(fig_account_trend, use_container_width=True)

st.divider()

# ===== 데이터 다운로드 =====
st.subheader("📥 데이터 다운로드")

col1, col2 = st.columns(2)

with col1:
    csv = filtered_df[['날짜', '계정', '비용', '연도', '월']].to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📊 필터된 데이터 CSV 다운로드",
        data=csv,
        file_name=f"IT비용_필터_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

with col2:
    full_csv = df[['날짜', '계정', '비용', '연도', '월']].to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📊 전체 데이터 CSV 다운로드",
        data=full_csv,
        file_name=f"IT비용_전체_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

st.divider()

# ===== AI 대화 =====
st.subheader("🤖 AI 데이터 분석 대화")
st.markdown("현재 대시보드 데이터를 기반으로 궁금한 점을 질문하세요.")

def get_data_summary(dataframe):
    """AI에게 전달할 데이터 요약 생성"""
    account_totals = dataframe.groupby('계정')['비용'].sum().sort_values(ascending=False)
    yearly_totals = dataframe.groupby('연도')['비용'].sum().sort_values()
    monthly_avg = dataframe.groupby('월')['비용'].mean()

    summary = f"""
현재 필터링된 IT 비용 데이터 요약:
- 기간: {dataframe['날짜'].min().strftime('%Y-%m')} ~ {dataframe['날짜'].max().strftime('%Y-%m')}
- 총 비용: ₩{dataframe['비용'].sum():,.0f}
- 평균 월간 비용: ₩{dataframe['비용'].mean():,.0f}
- 최고 비용(월): ₩{dataframe['비용'].max():,.0f}
- 계정 수: {dataframe['계정'].nunique()}개

계정별 총 비용:
{account_totals.apply(lambda x: f'₩{x:,.0f}').to_string()}

연도별 총 비용:
{yearly_totals.apply(lambda x: f'₩{x:,.0f}').to_string()}

월별 평균 비용:
{monthly_avg.apply(lambda x: f'₩{x:,.0f}').to_string()}
"""
    return summary

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("데이터에 대해 질문하세요... (예: 가장 비용이 많은 계정은?)")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("분석 중..."):
            try:
                data_summary = get_data_summary(filtered_df)
                system_prompt = f"""당신은 IT 비용 데이터 분석 전문가입니다. 아래 데이터를 기반으로 사용자 질문에 한국어로 친절하고 명확하게 답변하세요.
숫자는 읽기 쉽게 천 단위 구분자와 ₩ 기호를 사용하세요.

{data_summary}"""

                model = genai.GenerativeModel("gemini-flash-latest")
                history_for_gemini = []
                for h in st.session_state.chat_history[:-1]:
                    role = "user" if h["role"] == "user" else "model"
                    history_for_gemini.append({"role": role, "parts": [h["content"]]})

                chat = model.start_chat(history=history_for_gemini)
                response = chat.send_message(f"{system_prompt}\n\n사용자 질문: {user_input}")
                answer = response.text
            except Exception as e:
                answer = f"❌ 오류가 발생했습니다: {str(e)}"

        st.markdown(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})

if st.session_state.chat_history:
    if st.button("🗑️ 대화 초기화"):
        st.session_state.chat_history = []
        st.rerun()

st.divider()

# ===== 데이터 통계 =====
with st.expander("📊 데이터 통계"):
    stats_col1, stats_col2 = st.columns(2)

    with stats_col1:
        st.write("**비용 통계**")
        st.write(f"최소값: ₩{filtered_df['비용'].min():,.2f}")
        st.write(f"평균값: ₩{filtered_df['비용'].mean():,.2f}")
        st.write(f"최대값: ₩{filtered_df['비용'].max():,.2f}")
        st.write(f"표준편차: ₩{filtered_df['비용'].std():,.2f}")

    with stats_col2:
        st.write("**데이터 범위**")
        st.write(f"기간: {filtered_df['날짜'].min().strftime('%Y-%m-%d')} ~ {filtered_df['날짜'].max().strftime('%Y-%m-%d')}")
        st.write(f"총 레코드: {len(filtered_df):,}개")
        st.write(f"계정 수: {filtered_df['계정'].nunique()}개")
        st.write(f"기간(개월): {len(filtered_df['날짜'].dt.to_period('M').unique())}개월")
