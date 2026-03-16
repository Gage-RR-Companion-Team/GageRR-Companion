# Gage R&R Companion
A companion tool to assist in developing and analyzing Gage R&R studies. This tool provides an interactive GUI that allows the user to import a formatted CSV of their results, then interperets and visualizes the results.


## What is Gage R&R?
Gage Repeatability and Reproducibility (Gage R&R) is a statistical method used in measurement systems analysis (MSA) to detemrmine how much variation in your measurements comes form the measurement system itself rather than the actual parts being measured. Essentially, it answers:
> "Can I trust my measurement process?"

## What does Gage R&R companion do?
This python program helps the user in interpreting the results of a Gage R&R study. This process often requries utilizing specialized statistical software that not everyone may have access to. 

This program provides a simple tool for analyzing Gage R&R results by allowing users to upload their measurement data in a CSV format and automatically generates key statistics and plots for visualization within an interactive GUI. The goal overall is to make it easier to quickly explore Gage R&R results, understand the sources of the measurement variation, and visually inspect its measurement behavior without needed to manually construct plots or compute metrics.

## Interface Images

![Home Page](/docs/images/home.png)
![Analysis Input](/docs/images/input.png)
![Metrics Summary](/docs/images/summary_metrics_interpretation.png)

## Key Features of Gage R&R Companion

* Upload Gage R&R Datasets from CSV
* Compute crossed Gage R&R metrics and provides summary metrics
* Provides interpretation of the results (acceptability)
* Root cause analysis of the data
* Plots consisting of respective control charts, measurement distributions, and variance contributions

## Installation

This program utilizes `python 3.12` for compatibility with streamlit and its dependencies.

To install the required dependencies, navigate to the top-level folder of the package and run

`pip install -e .`

This should install all the required python dependencies into your instance

To initiate the GUI for the program, from the top-level folder, run:

`streamlit run src/gage_rr_companion/app.py`

This will run a local web-app of the program that you can access through the link provided in the terminal.

## Quick Start

When opening the link provided in the terminal, you land on the landing page which provides a brief overview and buttons leading to pages for analysis as well as additional documentation. These can be accessed through the sidebar as well.

To begin analysis, the program currently requires a specifically formatted CSV of the Gage R&R study results. A table consisting of the formatting can be seen below

| Operator | Part | Trial | Value |
|----------|----------|----------|----------|
|  |  |  |

All values must be filled for analysis to be successful

When the CSV is uploaded, analysis will begin immediately and results will be shown on the same page.

## Scope

This program currently supports crossed Gage R&R studies utilizing ANOVA-based calculations.
It is intended for balanced datasets, and does not replace formal review by a quality engineer in regulated settings.

In the future, this program will provide more studies such as nested Gage R&R studies.


## Dependencies

* Python 3.12
* Streamlit 1.54.0
* pandas 2.0.0
* numpy 1.24.0
* altair 6.0.0

These are installed in the initial installation command with their respective depdencies as well.

## Additional Gage R&R Documention:
Below are additional resources for learning about Gage R&R.

1. ASQ - https://asq.org/quality-resources/gage-repeatability?srsltid=AfmBOoqWP1c-bsj5TwBh-o1X-QN3fSPi8bCMTsaI1BenUD8FpZA1H4h0
2. Six Sigma - https://sixsigmastudyguide.com/gage-repeatability-and-reproducibility-rr/ 
