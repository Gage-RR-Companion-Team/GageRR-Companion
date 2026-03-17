import streamlit as st

st.set_page_config(
    page_title='Gage R&R Companion',
    page_icon='📊',
    layout='centered'

)

st.sidebar.success('Welcome to the Gage R&R Companion!')

st.write("# Gage R&R Companion")

st.markdown(
    """
    This application allows you to perform Gage R&R analysis on your measurement system data. 
    Upload your data in CSV format, and the app will compute the ANOVA table, variance components, 
    Gage R&R table, operator statistics, and summary metrics for you.
    
    **Instructions:**
    1. Prepare your data in a CSV file with the following columns: `Operator`, `Part`, `Trial`, `Measurement`.
    2. Click on the "Upload your Gage R&R data" button below to upload your CSV file.
    3. View the results in the respective sections below.
    
    **Note:** Ensure that your data is properly formatted for accurate analysis.
    """
)

col1, col2, col3 = st.columns([1, 2, 3])

with col1:
    if st.button('Analyze Results'):
        st.switch_page('pages/1_Gage_RR_Analysis.py')

with col2:
    if st.button('Documentation'):
        st.switch_page('pages/2_Documentation.py')