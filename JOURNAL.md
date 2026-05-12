# 📓 UAE Real Estate AI Analyst - Project Journal

> **Objective:** Build a production-grade AI Agent for UAE real estate analytics.
> **Author:** [Your Name/Role]
> **Partner/Stakeholder:** [Partner's Name]

---

## 📅 2026-05-04 | Day 1: Project Initiation

### 🎯 Today's Goal
Establish the professional foundation for the codebase and environment.

### ✅ Progress Checklist
- [x] Project Structure Defined
- [x] Virtual Environment Created (`python -m venv venv`)
- [x] Git Repository Initialized & Cleaned
- [x] Core Dependencies Installed (`pip install -r requirements.txt` inside venv)

### 🧠 Decisions Made
| Component | Decision | Rationale |
| :--- | :--- | :--- |
| **Project Management** | Markdown Journaling | To provide transparency to stakeholders and track architectural "whys". |
| **Language** | Python 3.12.4 | Modern, stable, and industry-standard for AI/Data work. |
| **Dependency Management** | Virtual Environment (venv) | Isolates project libraries to prevent conflicts with other Python projects on the system. |
| **Database** | DuckDB 1.5.2 | No server required, $0 cost, blazing fast for analytical queries. Perfect for local MVP. |
| **LLM API** | Groq API (via LangChain) | Free tier, fastest inference in the world. Runs Llama models at no cost during development. |
| **UI Framework** | Streamlit 1.53.1 | Build interactive data web apps in pure Python. Zero HTML/CSS/JS required. |
| **Version Pinning** | `>=` in requirements.txt | Allows minor upgrades during dev. Will switch to `==` for production freeze. |
| **Version Control** | Git | Industry standard for tracking changes and collaborative engineering. |

### 🛑 Blockers / Challenges
- **Venv Tracking Issue:** Accidentally committed the `venv/` folder to Git.
- **Resolution:** Used `git rm -r --cached venv` to remove it from tracking without deleting the local files, then updated `.gitignore`.

### 💡 Lessons Learned
- Engineering is 50% planning and 50% execution.
- **Always activate venv before running pip install.** If you don't, libraries go into the global Python installation and can break other projects on your machine.
- `git add` = staging (packing the box). `git commit` = saving locally (sealing it). `git push` = sending to GitHub (putting it on a truck).
- Always check `.gitignore` is correct BEFORE the first `git add`.

---

## 📅 2026-05-08 | Day 2: Deep Dive Data Exploration

### 🎯 Today's Goal
Validate core data columns (`procedure_area`, `actual_worth`, `rent_value`) and identify data quality patterns.

### ✅ Progress Checklist
- [x] Validated `procedure_area` logic (Worth / Area = Price per SQM).
- [x] Analyzed magnitude of financial values.
- [x] Identified high sparsity in rental data (96%+ missing).

### 🧠 Decisions Made
| Component | Decision | Rationale |
| :--- | :--- | :--- |
| **Data Logic** | Validated Area Metric | Confirmed that `meter_sale_price` is a calculated field derived from `actual_worth` and `procedure_area`. |
| **Outlier Handling** | Suspicious Rent Values | Median rent (1M AED) vs Median Sale (1.25M AED) indicates `rent_value` might represent total contract value or building-level rent, not unit-level. Needs further segmentation. |

### 🛑 Blockers / Challenges
- **Data Sparsity:** `rent_value` and `meter_rent_price` are missing in over 96% of the records, meaning this dataset is primarily focused on Sales transactions.
- **Ambiguous Units:** "Unit" is the most common property type (68%), but it blends residential apartments and commercial offices.

### 💡 Lessons Learned
- **99.6% Consistency:** The math holds up for the area calculation, which gives us high confidence in the geometric and financial data recorded by DLD.
- **Sample Strategy:** Loading the first 100k rows is enough to spot massive trends without crashing the environment with the full 600MB file.
