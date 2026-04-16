Name: 

compute_type1.py

Dependencies:

pandas
numpy
scipy stats (For computing t statistic and getting p value)

What it does: 

Calculates all of the statistics for a Type1 gage study in addition to a dataframe of values to be used in a run chart

Inputs: 

Upstream of this a component will provide the following data

Name of study [string]
User [string]
Measurement Standard Value (X_m) [float]
Units of measurement [string]
Tolerance [float]
Data [DataFrame] (1 column of datatype=float)


Outputs: 

Mean (X_bar)
St. Dev (S)
Study Variation (SV = 6 * S) 
Bias (Bias = X_bar - X_m) 
t statistic (t)
p value from (t-test)
    alternate hypothesis = the population mean is significantly different than the standard (ie: there is significant bias)
    Test bias = 0

Capability indices 1 (C_g = (K/100)*Tolerance / SV)
Capability indices 2 (C_gk = ((K/200)*Tolerance - |X_bar - X_m|) / (SV/2))

% Var (Repeatability) = SV/Tolerance * 100 
% Var (Repeatability and Bias) = (20/C_gk)

Control Chart Parameters [DataFrame]:

X_bar_series = Series of n points, where n is the number of rows the user provides, and all values are the X_bar

LCL = X_bar_series - 3*S

UCL = X_bar_series + 3*S

Data_series = series of data from the user


How it uses other components: 

The inputs are going to be passed from another component 
The outputs are going to be incorporated into our GUI made in streamlit

The DataFrame for plotting will be plotted in altair as a run chart
