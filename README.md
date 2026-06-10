# Gage R&R Companion

Gage R&R Companion is a free, open source measurement systems analysis 
tool that makes it easy to analyze Gage R&R study data without needing 
access to expensive software like Minitab.

## 💻 What does Gage R&R Companion do?

Gage Repeatability and Reproducibility (Gage R&R) is a statistical method 
used to determine how much variation in your measurements comes from the 
measurement system itself rather than the actual parts being measured.

Gage R&R Companion lets you upload your measurement data as a CSV file 
and automatically computes key metrics, generates visualizations, and 
interprets your results through an interactive GUI. It also includes an 
AI chatbot that can recommend the right study type for your situation and 
generate a properly formatted data collection template for you.

## 🖼️ Interface

![Home Page](/docs/images/home.png)
![Analysis Input](/docs/images/input.png)
![Metrics Summary](/docs/images/summary_metrics_interpretation.png)

## 🔑 Key Features

- Upload Gage R&R datasets from CSV
- Supports Crossed, Nested, Expanded, and Type 1 study types
- Computes variance components, summary metrics, and ANOVA tables
- Automatic interpretation of results including acceptability and root 
cause analysis
- Interactive plots including control charts, measurement distributions, 
and variance contributions
- AI chatbot (Cornelius) for study type recommendations and template 
generation

## 📐 Study Types

Gage R&R Companion supports four study types. For full descriptions of 
each and guidance on which to use, see the 
[Study Types](https://github.com/Gage-RR-Companion-Team/GageRR-Companion/wiki/Study-Types) 
wiki page.

- **Crossed** - Every operator measures every part. The most common 
study type for non-destructive parts.
- **Nested** - Each operator measures a unique set of parts. Used when 
parts cannot be shared across operators.
- **Type 1** - Single operator study used to evaluate the gage itself 
before a full study.
- **Expanded** - Extends the crossed design to include additional sources 
of variation such as fixtures or measurement sites. Intended for 
experienced users.

## 💾 Installation

This program requires Python 3.12 or higher.

Navigate to the top-level folder of the project and run:

```
pip install -e ".[local]" --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

Download the default local Cornelius model:

```
gage_rr_companion download-local-model
```

Then in the same terminal instance run:

```
gage_rr_companion
```

This will launch a local web app accessible through the link provided 
in the terminal. A `.streamlit/secrets.toml` file is only needed if you
want to add private API keys or override the default model settings.

For detailed installation instructions including conda setup and AI 
chatbot configuration, see the 
[Installation and Setup](https://github.com/Gage-RR-Companion-Team/GageRR-Companion/wiki/Installation-and-Setup) 
wiki page.

## ▶️ Quick Start

When the app opens you will land on the Home page. Navigate to the 
Gage R&R Analysis page using the sidebar or the "Analyze Results" button.

1. Select your study type
2. Upload your CSV file
3. Results generate automatically

Your CSV file must contain the following columns: `Operator`, `Part`, 
`Trial`, and `Value`. All cells must be filled. For full formatting 
requirements see the 
[Input File Specifications](https://github.com/Gage-RR-Companion-Team/GageRR-Companion/wiki/Input-File-Specifications) 
wiki page.

Not sure which study type to use or how to format your file? Chat with 
Cornelius, the built-in AI assistant, accessible from the sidebar. See 
the 
[AI Chatbot Guide](https://github.com/Gage-RR-Companion-Team/GageRR-Companion/wiki/AI-Chatbot-Guide) 
for setup instructions.

## 📖 Documentation

Full documentation is available in the 
[project wiki](https://github.com/Gage-RR-Companion-Team/GageRR-Companion/wiki), 
including a user guide, study type explanations, statistical methodology, 
and result interpretation guidance.

## Dependencies

- Python 3.12
- Streamlit 1.54.0
- pandas 2.0.0
- numpy 1.24.0
- scipy 1.10.0
- statsmodels 0.14.6
- altair 6.0.0
- huggingface_hub 0.36.0
- openpyxl 3.1.0
