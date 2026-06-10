import streamlit as st

st.title("Hello Streamlit! 👋")
st.write("Streamlit을 프로젝트에서 처음 사용하고 있습니다.")

name = st.text_input("이름을 입력하세요:")
if name:
    st.write(f"안녕하세요, {name}님!")
