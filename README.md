# Gage R&R Companion
A companion tool to assist in developing and analyzing Gage R&R studies. This tool provides an interactive GUI that allows the user to import a formatted CSV of their results, then interperets and visualizes the results.


## ❔ What is Gage R&R?
Gage Repeatability and Reproducibility (Gage R&R) is a statistical method used in measurement systems analysis (MSA) to detemrmine how much variation in your measurements comes form the measurement system itself rather than the actual parts being measured. Essentially, it answers:
> "Can I trust my measurement process?"

## 💻 What does Gage R&R companion do?
This python program helps the user in interpreting the results of a Gage R&R study. This process often requries utilizing specialized statistical software that not everyone may have access to. 

This program provides a simple tool for analyzing Gage R&R results by allowing users to upload their measurement data in a CSV format and automatically generates key statistics and plots for visualization within an interactive GUI. The goal overall is to make it easier to quickly explore Gage R&R results, understand the sources of the measurement variation, and visually inspect its measurement behavior without needed to manually construct plots or compute metrics.

## 🖼️ Interface Images

![Home Page](/docs/images/home.png)
![Analysis Input](/docs/images/input.png)
![Metrics Summary](/docs/images/summary_metrics_interpretation.png)

## 🔑 Key Features of Gage R&R Companion
* Upload Gage R&R Datasets from CSV
* Compute Gage R&R metrics across multiple study types — including Crossed, Expanded, Type 1, and Nested — and provides summary metrics for each
* Provides interpretation of the results (acceptability)
* Root cause analysis of the data
* Plots consisting of respective control charts, measurement distributions, and variance contributions
## 📐 Gage R&R Study Types
Gage R&R encompasses several distinct study types, each suited to different measurement system scenarios. Understanding which study to use is critical to obtaining meaningful results.
 
### Crossed Gage R&R
In a crossed study, every operator measures every part, and every part is measured multiple times by each operator. This is the most common study type and is ideal when it is practical for all operators to measure all parts.
 
**When to use it:**
- The parts are non-destructive and can be re-measured
- You have a relatively small number of parts and operators
- You want to isolate and quantify both repeatability (equipment variation) and reproducibility (operator variation)
- You want to assess the interaction between operators and parts
### Expanded Gage R&R
An expanded study builds on the crossed design by incorporating additional sources of variation beyond just operators and parts — for example, different fixtures, environmental conditions, measurement locations, or time periods. It follows a structured ANOVA approach but with an extended factor model.
 
**When to use it:**
- You suspect significant variation from sources other than the operator or the gage itself
- You need to evaluate a measurement system across multiple sites, shifts, or setups
- You want a more comprehensive picture of all factors contributing to measurement variation
### Type 1 Gage Study
A Type 1 study is a simplified, single-operator study used to evaluate only the **gage itself** — specifically its bias (accuracy) and repeatability (precision) — independent of operator influence. It is typically a preliminary study run before a full Gage R&R.
 
**When to use it:**
- You want to qualify a new piece of measurement equipment before deploying it
- You need to isolate and understand the inherent capability and bias of the gage alone
- You are performing an initial screening before committing to a full crossed or nested study
- Only one operator is available, or operator variation is not a concern
### Nested Gage R&R
In a nested study, parts are not shared across operators — each operator measures a **unique set of parts**. This nesting structure means operator and part effects cannot be fully separated in the same way as a crossed study, but it reflects real-world scenarios where re-measurement by multiple operators is impractical.
 
**When to use it:**
- Parts are destructive or consumed during measurement (e.g., tensile testing, chemical analysis)
- Parts cannot be physically passed between operators due to handling, contamination, or traceability concerns
- Each operator works with their own distinct batch or sample of parts
- A crossed design is logistically infeasible


## 💾 Installation

This program utilizes `python 3.12` for compatibility with streamlit and its dependencies.

To install the required dependencies, navigate to the top-level folder of the package and run

`pip install -e .`

This should install all the required python dependencies into your instance

Within the instance where the package is downloaded, you can run the following command:

`gage_rr_companion`

This will run a local web-app of the program that you can access through the link provided in the terminal.

## ▶️ Quick Start

When opening the link provided in the terminal, you land on the landing page which provides a brief overview and buttons leading to pages for analysis as well as additional documentation. These can be accessed through the sidebar as well.

To begin analysis, the program currently requires a specifically formatted CSV of the Gage R&R study results. A table consisting of the formatting can be seen below

| Operator | Part | Trial | Value |
|----------|----------|----------|----------|
|  |  |  |

All values must be filled for analysis to be successful

When the CSV is uploaded, analysis will begin immediately and results will be shown on the same page.

## 🔬 Scope

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
