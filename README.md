# 🔍 FactCheck AI — Truth Layer

A deployed Streamlit web app that automatically fact-checks PDFs by extracting verifiable claims and cross-referencing them against live web data using Gemini.

## 🚀 Live Demo

> **Deployed App:** `https://factcheck-ai-9v7npaz23hhqzyqhzptetv.streamlit.app/`
> 

## 🎯 What It Does

| Step | Action |
|------|--------|
| 1 | **Extract** — Reads your PDF and identifies specific claims (stats, dates, financial/technical figures) |
| 2 | **Verify** — Uses Gemini + Google Search grounding to check each claim against current authoritative data |
| 3 | **Report** — Flags every claim as ✅ Verified, ⚠️ Inaccurate, ❌ False, or ❓ Unverifiable |

## 📦 Setup

### Local Development

```bash
# 1. Clone the repo
git clone https://github.com/harshkharb02/factcheck-ai.git
cd factcheck-ai

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

You'll be prompted to enter your Gemini API key in the sidebar.

## 🏗️ Architecture

```
PDF Upload
    │
    ▼
pdfplumber (text extraction)
    │
    ▼
Gemini 2.5 Flash (claim extraction)
    │  → Returns: [{claim, category, context}, ...]
    ▼
Gemini 2.5 Flash + Google Search tool (per-claim verification)
    │  → Returns: {verdict, confidence, analysis, real_fact, sources}
    ▼
Streamlit UI (color-coded results dashboard)
```

## 🔑 Models Used

- **Model:** `gemini-2.5-flash`
- **Tool:** `google_search` (Gemini built-in grounding)

## 📊 Verdict Definitions

| Verdict | Meaning |
|---------|---------|
| ✅ **VERIFIED** | Claim matches current authoritative data |
| ⚠️ **INACCURATE** | Claim is outdated, partially wrong, or uses wrong figures |
| ❌ **FALSE** | Claim is directly contradicted by web evidence |
| ❓ **UNVERIFIABLE** | Insufficient public evidence to confirm or deny |

## 📁 File Structure

```
factcheck-ai/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## ⚙️ Configuration

| Setting | Value |
|---------|-------|
| Max claims extracted | 20 per document |
| Max PDF text analyzed | 8,000 characters |
| Rate limit buffer | 0.3s between verifications |

## 🧪 Testing with a "Trap Document"

The app is specifically designed to catch intentional lies and outdated statistics. To test:
1. Create a PDF with known false stats (e.g., "ChatGPT was launched in 2018")
2. Upload it to the app
3. The app should flag it as **FALSE** with the correct launch year

## 📄 License

MIT — free to use and modify.
