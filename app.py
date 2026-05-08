import streamlit as st
import pdfplumber
from google import genai
from google.genai import types
import json
import re
import time
from io import BytesIO

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FactCheck AI — Truth Layer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  
  .main-header {
    background: linear-gradient(135deg, #0A1628 0%, #0D3050 100%);
    padding: 2rem 2.5rem;
    border-radius: 12px;
    margin-bottom: 2rem;
    border-left: 5px solid #14B8A6;
  }
  .main-header h1 { color: #FFFFFF; margin: 0; font-size: 2rem; }
  .main-header p  { color: #94A3B8; margin: 0.5rem 0 0; font-size: 1rem; }

  .verdict-verified {
    background: #F0FDF4; border: 1.5px solid #16A34A; border-radius: 10px;
    padding: 1rem 1.2rem; margin: 0.6rem 0;
  }
  .verdict-inaccurate {
    background: #FFFBEB; border: 1.5px solid #D97706; border-radius: 10px;
    padding: 1rem 1.2rem; margin: 0.6rem 0;
  }
  .verdict-false {
    background: #FEF2F2; border: 1.5px solid #DC2626; border-radius: 10px;
    padding: 1rem 1.2rem; margin: 0.6rem 0;
  }
  .verdict-unverifiable {
    background: #F8FAFC; border: 1.5px solid #94A3B8; border-radius: 10px;
    padding: 1rem 1.2rem; margin: 0.6rem 0;
  }

  .badge-verified    { background:#16A34A; color:#fff; padding:3px 10px; border-radius:99px; font-size:0.72rem; font-weight:700; }
  .badge-inaccurate  { background:#D97706; color:#fff; padding:3px 10px; border-radius:99px; font-size:0.72rem; font-weight:700; }
  .badge-false       { background:#DC2626; color:#fff; padding:3px 10px; border-radius:99px; font-size:0.72rem; font-weight:700; }
  .badge-unverifiable{ background:#94A3B8; color:#fff; padding:3px 10px; border-radius:99px; font-size:0.72rem; font-weight:700; }

  .claim-text  { font-size: 0.95rem; font-weight: 600; color: #1E293B; margin: 0.4rem 0 0.3rem; }
  .analysis    { font-size: 0.85rem; color: #475569; line-height: 1.5; }
  .real-fact   { font-size: 0.85rem; color: #0D9488; font-weight: 600; margin-top: 0.4rem; }
  .sources-tag { font-size: 0.75rem; color: #94A3B8; margin-top: 0.3rem; }

  .stats-box {
    background: #F8FAFC; border: 1px solid #E2E8F0;
    border-radius: 10px; padding: 1rem 1.5rem; text-align: center;
  }
  .stats-num  { font-size: 2rem; font-weight: 700; color: #0A1628; }
  .stats-lbl  { font-size: 0.8rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; }

  .step-indicator {
    background: #EEF2FF; border-radius: 8px; padding: 0.5rem 1rem;
    font-size: 0.85rem; color: #4338CA; font-weight: 500; margin-bottom: 1rem;
  }
</style>
""", unsafe_allow_html=True)

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>🔍 FactCheck AI — Truth Layer</h1>
  <p>Upload a PDF → AI extracts every verifiable claim → cross-references live web data → flags what's true, outdated, or false</p>
</div>
""", unsafe_allow_html=True)

# ─── API Key input ─────────────────────────────────────────────────────────────
try:
    default_api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    default_api_key = ""

with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        value=default_api_key,
        help="Get your key at aistudio.google.com/app/apikey",
    )
    st.markdown("---")
    st.markdown("**How it works:**")
    st.markdown("1. 📄 Extract text from your PDF")
    st.markdown("2. 🧠 AI identifies verifiable claims")
    st.markdown("3. 🌐 Each claim is verified via web search")
    st.markdown("4. 📊 Results flagged as Verified / Inaccurate / False")
    st.markdown("---")
    st.markdown("**Verdict Guide:**")
    st.markdown("✅ **Verified** — matches current data")
    st.markdown("⚠️ **Inaccurate** — outdated or partially wrong")
    st.markdown("❌ **False** — contradicted by evidence")
    st.markdown("❓ **Unverifiable** — can't confirm or deny")

# ─── Helper: extract text from PDF ────────────────────────────────────────────
def extract_pdf_text(uploaded_file) -> str:
    text_parts = []
    with pdfplumber.open(BytesIO(uploaded_file.read())) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n\n".join(text_parts)

# ─── Helper: parse JSON from model output ─────────────────────────────────────
def parse_json_payload(raw_text: str):
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```json\s*|^```\s*|\s*```$", "", cleaned, flags=re.MULTILINE).strip()
    return json.loads(cleaned)

def generate_text(client: genai.Client, prompt: str, use_web_search: bool = False) -> str:
    config = types.GenerateContentConfig()
    if use_web_search:
        config.tools = [types.Tool(google_search=types.GoogleSearch())]
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=config,
    )
    return response.text or ""

# ─── Helper: extract claims via Gemini ────────────────────────────────────────
def extract_claims(client: genai.Client, doc_text: str) -> list[dict]:
    prompt = f"""You are a precise fact-extraction engine. Analyze the document below and extract ALL verifiable factual claims.

Focus on:
- Statistics and percentages (e.g., "market grew by 45%")
- Dates and timelines (e.g., "launched in 2021")
- Financial figures (e.g., "valued at $2 billion")  
- Technical specifications (e.g., "processes 10,000 requests/second")
- Named rankings or positions (e.g., "#1 in Europe")
- Scientific or research claims with specific numbers
- Named events with specific dates or outcomes

IGNORE: opinions, vague statements, future predictions without cited basis.

Return ONLY a valid JSON array (no markdown, no explanation):
[
  {{
    "claim": "exact quote or close paraphrase of the claim from the document",
    "category": "statistic|date|financial|technical|ranking|research",
    "context": "brief surrounding context (1 sentence)"
  }},
  ...
]

Extract between 5 and 20 claims. Prioritize the most specific, checkable claims.

DOCUMENT:
{doc_text[:8000]}"""

    output = generate_text(client, prompt, use_web_search=False)
    return parse_json_payload(output)

# ─── Helper: verify a single claim via Gemini + Google search ────────────────
def verify_claim(client: genai.Client, claim: dict) -> dict:
    prompt = f"""You are a rigorous fact-checker. Verify this claim using Google Search:

CLAIM: "{claim['claim']}"
CATEGORY: {claim['category']}
CONTEXT: {claim['context']}

Instructions:
1. Search the web for current, authoritative information about this claim
2. Compare what you find to the claim
3. Return ONLY a JSON object (no markdown, no explanation):

{{
  "verdict": "VERIFIED" | "INACCURATE" | "FALSE" | "UNVERIFIABLE",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "analysis": "2-3 sentence explanation of your finding",
  "real_fact": "The correct/current fact if the claim is wrong or outdated (null if verified)",
  "sources": ["source name or URL snippet", ...]
}}

Verdict guide:
- VERIFIED: claim matches current authoritative data
- INACCURATE: claim is outdated, partially wrong, or uses wrong figures  
- FALSE: claim is directly contradicted by evidence
- UNVERIFIABLE: insufficient evidence found to confirm or deny"""

    result_text = generate_text(client, prompt, use_web_search=True).strip()
    try:
        result = parse_json_payload(result_text)
    except Exception:
        # Fallback if JSON parse fails
        result = {
            "verdict": "UNVERIFIABLE",
            "confidence": "LOW",
            "analysis": result_text[:300] if result_text else "Could not parse verification result.",
            "real_fact": None,
            "sources": []
        }

    result["claim"] = claim["claim"]
    result["category"] = claim["category"]
    result["context"] = claim["context"]
    return result

# ─── Helper: render a single result card ──────────────────────────────────────
def render_result_card(result: dict, index: int):
    verdict = result.get("verdict", "UNVERIFIABLE")
    confidence = result.get("confidence", "LOW")
    analysis = result.get("analysis", "")
    real_fact = result.get("real_fact")
    sources = result.get("sources", [])

    css_class = {
        "VERIFIED": "verdict-verified",
        "INACCURATE": "verdict-inaccurate",
        "FALSE": "verdict-false",
        "UNVERIFIABLE": "verdict-unverifiable",
    }.get(verdict, "verdict-unverifiable")

    badge_class = {
        "VERIFIED": "badge-verified",
        "INACCURATE": "badge-inaccurate",
        "FALSE": "badge-false",
        "UNVERIFIABLE": "badge-unverifiable",
    }.get(verdict, "badge-unverifiable")

    emoji = {"VERIFIED": "✅", "INACCURATE": "⚠️", "FALSE": "❌", "UNVERIFIABLE": "❓"}.get(verdict, "❓")

    sources_html = ""
    if sources:
        sources_html = f'<div class="sources-tag">Sources: {" · ".join(str(s) for s in sources[:3])}</div>'

    real_fact_html = ""
    if real_fact:
        real_fact_html = f'<div class="real-fact">📌 Correct fact: {real_fact}</div>'

    conf_color = {"HIGH": "#16A34A", "MEDIUM": "#D97706", "LOW": "#DC2626"}.get(confidence, "#94A3B8")

    st.markdown(f"""
    <div class="{css_class}">
      <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;">
        <span class="{badge_class}">{emoji} {verdict}</span>
        <span style="font-size:0.75rem; color:{conf_color}; font-weight:600;">● {confidence} confidence</span>
        <span style="font-size:0.72rem; color:#94A3B8; margin-left:auto;">#{index+1} · {result.get('category','').upper()}</span>
      </div>
      <div class="claim-text">"{result.get('claim','')}"</div>
      <div class="analysis">{analysis}</div>
      {real_fact_html}
      {sources_html}
    </div>
    """, unsafe_allow_html=True)

# ─── Main UI ──────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "📄 Upload your PDF document",
    type=["pdf"],
    help="Any PDF containing factual claims, stats, or data"
)

if uploaded_file:
    if not api_key:
        st.warning("⚠️ Please enter your Gemini API key in the sidebar to continue.")
        st.stop()

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.success(f"✅ Uploaded: **{uploaded_file.name}** ({round(uploaded_file.size/1024, 1)} KB)")
    with col3:
        run_btn = st.button("🚀 Run Fact Check", type="primary", use_container_width=True)

    if run_btn:
        client = genai.Client(api_key=api_key)

        # Step 1: Extract PDF text
        with st.spinner("📄 Extracting text from PDF..."):
            try:
                doc_text = extract_pdf_text(uploaded_file)
            except Exception as e:
                st.error(f"Failed to read PDF: {e}")
                st.stop()

        if not doc_text.strip():
            st.error("Could not extract text from this PDF. It may be scanned/image-based.")
            st.stop()

        with st.expander("📃 View extracted text (first 2000 chars)", expanded=False):
            st.text(doc_text[:2000] + ("..." if len(doc_text) > 2000 else ""))

        # Step 2: Extract claims
        st.markdown('<div class="step-indicator">🧠 Step 2/3 — Identifying verifiable claims...</div>', unsafe_allow_html=True)
        with st.spinner("Analysing document for factual claims..."):
            try:
                claims = extract_claims(client, doc_text)
            except Exception as e:
                st.error(f"Claim extraction failed: {e}")
                st.stop()

        st.info(f"🎯 Found **{len(claims)} verifiable claims** to fact-check")

        # Step 3: Verify each claim
        st.markdown('<div class="step-indicator">🌐 Step 3/3 — Verifying claims against live web data...</div>', unsafe_allow_html=True)

        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, claim in enumerate(claims):
            status_text.markdown(f"🔍 Checking claim {i+1}/{len(claims)}: *\"{claim['claim'][:80]}...\"*")
            try:
                result = verify_claim(client, claim)
                results.append(result)
            except Exception as e:
                results.append({
                    "claim": claim["claim"],
                    "category": claim.get("category", "unknown"),
                    "context": claim.get("context", ""),
                    "verdict": "UNVERIFIABLE",
                    "confidence": "LOW",
                    "analysis": f"Verification failed: {str(e)}",
                    "real_fact": None,
                    "sources": []
                })
            progress_bar.progress((i + 1) / len(claims))
            time.sleep(0.3)  # rate limit buffer

        progress_bar.empty()
        status_text.empty()

        # ── Results Summary ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("## 📊 Fact-Check Report")

        counts = {
            "VERIFIED": sum(1 for r in results if r.get("verdict") == "VERIFIED"),
            "INACCURATE": sum(1 for r in results if r.get("verdict") == "INACCURATE"),
            "FALSE": sum(1 for r in results if r.get("verdict") == "FALSE"),
            "UNVERIFIABLE": sum(1 for r in results if r.get("verdict") == "UNVERIFIABLE"),
        }
        total = len(results)

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(f'<div class="stats-box"><div class="stats-num">{total}</div><div class="stats-lbl">Total Claims</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stats-box" style="border-color:#16A34A"><div class="stats-num" style="color:#16A34A">{counts["VERIFIED"]}</div><div class="stats-lbl">✅ Verified</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stats-box" style="border-color:#D97706"><div class="stats-num" style="color:#D97706">{counts["INACCURATE"]}</div><div class="stats-lbl">⚠️ Inaccurate</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="stats-box" style="border-color:#DC2626"><div class="stats-num" style="color:#DC2626">{counts["FALSE"]}</div><div class="stats-lbl">❌ False</div></div>', unsafe_allow_html=True)
        with c5:
            accuracy = round(counts["VERIFIED"] / total * 100) if total > 0 else 0
            st.markdown(f'<div class="stats-box"><div class="stats-num">{accuracy}%</div><div class="stats-lbl">Accuracy Score</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Filter tabs ──────────────────────────────────────────────────────
        tab_all, tab_flag, tab_ver = st.tabs([
            f"All Results ({total})",
            f"🚨 Flagged ({counts['INACCURATE'] + counts['FALSE']})",
            f"✅ Verified ({counts['VERIFIED']})"
        ])

        with tab_all:
            for i, r in enumerate(results):
                render_result_card(r, i)

        with tab_flag:
            flagged = [r for r in results if r.get("verdict") in ("INACCURATE", "FALSE")]
            if flagged:
                for i, r in enumerate(flagged):
                    render_result_card(r, i)
            else:
                st.success("🎉 No flagged claims — all verified or unverifiable!")

        with tab_ver:
            verified = [r for r in results if r.get("verdict") == "VERIFIED"]
            if verified:
                for i, r in enumerate(verified):
                    render_result_card(r, i)
            else:
                st.info("No claims could be fully verified.")

        # ── Download JSON ────────────────────────────────────────────────────
        st.markdown("---")
        report = {
            "document": uploaded_file.name,
            "total_claims": total,
            "summary": counts,
            "accuracy_score": f"{accuracy}%",
            "results": results
        }
        st.download_button(
            label="⬇️ Download Full Report (JSON)",
            data=json.dumps(report, indent=2),
            file_name=f"factcheck_{uploaded_file.name.replace('.pdf','')}.json",
            mime="application/json"
        )

else:
    # Landing state
    st.markdown("""
    <div style="text-align:center; padding:3rem 1rem; color:#64748B;">
      <div style="font-size:4rem;">📄</div>
      <h3 style="color:#1E293B;">Upload a PDF to get started</h3>
      <p>The AI will extract all verifiable claims and cross-reference them against live web data</p>
      <p style="font-size:0.85rem;">Works best on: marketing content, research reports, press releases, whitepapers, news articles</p>
    </div>
    """, unsafe_allow_html=True)
