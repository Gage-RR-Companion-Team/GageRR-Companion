import streamlit as st
st.set_page_config(page_title='Gage R&R Companion', layout='wide')

st.title('Gage R&R Companion')

data = st.file_uploader('Upload your Gage R&R data (CSV format)', type='csv')