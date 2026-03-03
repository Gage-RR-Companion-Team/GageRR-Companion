import streamlit as st
from compute import ComputeGageRR
from gage_rr_io import load_gage_rr_data
st.set_page_config(page_title='Gage R&R Companion', layout='centered')

st.title('Gage R&R Companion')

data = st.file_uploader('Upload your Gage R&R data (CSV format)', type='csv')

if data:
    import pandas as pd
    df = load_gage_rr_data(data, is_path=False)
    results = ComputeGageRR(df)
    st.subheader('ANOVA Table')
    st.dataframe(results['anova_table'])
    st.subheader('Variance Components')
    st.dataframe(results['variance_components'])
    st.subheader('Gage R&R Table')
    st.dataframe(results['gage_rr_table'])
    st.subheader('Operator Statistics')
    st.dataframe(results['operator_stats'])
    st.subheader('Summary Metrics')
    st.json(results['summary_metrics'])

