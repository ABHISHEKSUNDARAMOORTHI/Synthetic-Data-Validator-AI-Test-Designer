# 🧪 Synthetic Data Validator + AI Test Designer

> **🧠 "Validate, Fix, and Enhance Test Datasets Automatically with AI."**

---

## ✨ Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [How It Works (Under the Hood)](#how-it-works-under-the-hood)
- [Visual Elements & UX](#visual-elements--ux)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)

  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Google Gemini API Key Setup](#google-gemini-api-key-setup)
  - [Running the Application](#running-the-application)

- [Usage Guide](#usage-guide)
- [Sample Files (for Testing)](#sample-files-for-testing)
- [Project Structure](#project-structure)
- [Future Enhancements](#future-enhancements)
- [License](#license)
- [Contributing](#contributing)

---

## 📊 Project Overview

The **Synthetic Data Validator + AI Test Designer** is a powerful Streamlit application designed for QA, testing, and data engineering teams. It validates synthetic (or real) data against schema contracts (YAML/JSON), identifies gaps or issues, and uses **Google Gemini** to suggest schema improvements or generate better test scenarios.

It enhances **test automation**, improves **data quality**, and provides AI-powered insights to build more robust pipelines.

---

## ✨ Key Features

### 1. Input Validation

- Schema Upload: YAML or JSON (OpenAPI/JSONSchema)
- Synthetic Data Upload: CSV or JSON
- AI Validation: Format/type/rules/constraints checked

### 2. Constraint Coverage Checker

- Detects missing required fields or under-tested constraints
- Flags weak test coverage (e.g., enum, min/max not fully hit)

### 3. 🧑‍🧠 AI Suggestions (Gemini)

- Test Enhancement: Generate better edge cases
- Schema Fixes: Recommend format fields, stricter types, nullable flags

### 4. AI-Powered Test Case Generator

- Describe → Gemini → Test Cases
- Schema-based or inferred schema support
- Generate negative, edge, or boundary cases

### 5. AI Summary & Exports

- Markdown AI Reports with:

  - ⛔ Errors
  - ⚠️ Warnings
  - 💡 Suggestions

- Download CSV of failed cases or generated test data

---

## 🛠️ How It Works (Under the Hood)

### 1. Input & Parsing

- Upload: schema + synthetic data
- Parsed by: `file_utils.py`, `schema_parser.py`
- Preview shown in UI

### 2. Validation Engine (`data_checker.py`)

- Uses `jsonschema` to validate rows
- Custom checks for min/max, enums, nulls, required
- Generates structured report

### 3. AI Layer (Gemini)

- `ai_suggester.py`:

  - Suggest fixes/improvements to data/schema

- `test_case_generator.py`:

  - Generate edge cases / test sets from schema
  - Reverse engineer schema from data

### 4. Reporting & Export

- Markdown reports
- Export failed test data / AI-generated data

---

## 📈 Visual Elements & UX

- ✅ Fail / ⚠️ Warn / 🛑 Error indicators
- JSON & DataFrame viewers
- Progress indicators for coverage
- Custom dark mode CSS
- Download buttons for report/data

---

## 🚀 Tech Stack

- **IDE**: Visual Studio Code
- **Frontend**: Streamlit + custom CSS
- **AI**: Google Gemini (`gemini-1.5-flash-latest`)
- **Validation**: `jsonschema`, `pyyaml`
- **Data**: `pandas`
- **Reporting**: Markdown, CSV
- **Viz**: Altair, Matplotlib
- **Env**: `python-dotenv`, `venv`

---

## ✨ Getting Started

### Prerequisites

- Python 3.8+
- `pip`
- Git (optional)

### Installation

```bash
git clone https://github.com/your-username/synthetic-validator.git
cd synthetic-validator
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

### requirements.txt

```
streamlit==1.36.0
pandas==2.2.2
pyyaml==6.0.1
jsonschema==4.22.0
google-generativeai==0.6.0
python-dotenv==1.0.1
altair==5.3.0
matplotlib==3.9.0
scikit-learn==1.5.0
```

```bash
pip install -r requirements.txt
```

### Google Gemini API Key Setup

```
# .env
GEMINI_API_KEY="YOUR_API_KEY_HERE"
```

Don't share `.env` file publicly.

---

### Running the Application

```bash
streamlit run app.py
```

Opens: [http://localhost:8501](http://localhost:8501)

> ❗ Tip: Disable AI extras in sidebar if you hit quota limits.

---

## 🔄 Usage Guide

### 1. Upload Schema + Data

- YAML/JSON + CSV/JSON accepted
- Shows preview and structure

### 2. Validate & Get Insights

- Click "Run Validation & Get AI Insights"
- Review pass/fail summary, validation errors
- AI gives improvement tips (if enabled)

### 3. Generate AI Test Cases

- Describe what test cases you want
- Use slider to set number of records
- Option to reverse engineer schema from data

### 4. Export

- Download report (Markdown)
- Download failed rows (CSV)
- Download new test cases (CSV)

---

## 📃 Sample Files (for Testing)

```
synthetic-validator/sample_data/
├── contract_schema.yaml
└── synthetic_data.csv
```

---

## 📂 Project Structure

```
synthetic-validator/
├── .env
├── app.py
├── requirements.txt
├── README.md
├── validator/
│   ├── schema_parser.py
│   ├── data_checker.py
│   ├── ai_suggester.py
│   └── test_case_generator.py
├── utils/
│   ├── file_utils.py
│   └── logging_utils.py
├── reports/
│   └── export_utils.py
└── sample_data/
    ├── contract_schema.yaml
    └── synthetic_data.csv
```

---

## 🚀 Future Enhancements

- Better AI-driven schema inference (nested arrays/objects)
- Inline schema editor in UI
- Heatmaps for test coverage
- Faker support for test generation
- Git integration for schema version control
- Data catalog integrations

---

## 📄 License

[MIT License](LICENSE)

---

## 🙌 Contributing

Pull requests welcome! Bug reports & feedback appreciated.
