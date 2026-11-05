import json
import os
import re
from decimal import Decimal, InvalidOperation

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="BillSaathi AI", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# ---------- Visual system ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --ink:#eaf2f8; --muted:#8ea2b5; --teal:#39d6c3; --panel:#101d2b; --panel2:#142538; --line:rgba(164,190,211,.13); }
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
.stApp {background:radial-gradient(ellipse at 12% 0%,rgba(30,112,124,.19),transparent 35%),linear-gradient(145deg,#07121f 0%,#0b1725 55%,#0a1925 100%); color:var(--ink);}
.block-container {max-width:1440px;padding-top:1.45rem;padding-bottom:3rem;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#0c1b2a,#0a1522);border-right:1px solid var(--line);}
[data-testid="stSidebar"] * {color:#dce8f1;}
h1,h2,h3,h4 {font-family:'Manrope',sans-serif;letter-spacing:-.035em;color:#f1f7fb;}
p, label, .stMarkdown {color:#d6e2ec;}
div[data-testid="stMetric"] {background:linear-gradient(145deg,rgba(22,42,61,.95),rgba(15,30,45,.95));border:1px solid var(--line);padding:17px 19px;border-radius:17px;box-shadow:0 12px 32px rgba(0,0,0,.12);}
div[data-testid="stMetricLabel"] p {color:#9db1c3!important;font-size:.83rem;}
div[data-testid="stMetricValue"] {color:#f4fbff!important;font-family:'Manrope',sans-serif;}
div[data-testid="stMetricDelta"] {font-size:.78rem;}
.stButton>button {border-radius:11px;border:1px solid rgba(57,214,195,.25);background:linear-gradient(100deg,#22b9ae,#39d6c3);color:#06202a;font-weight:800;min-height:2.8rem;transition:all .2s;}
.stButton>button:hover {border-color:#7af5e5;background:linear-gradient(100deg,#39d6c3,#6cebdc);color:#06202a;transform:translateY(-1px);}
.stDownloadButton>button {border-radius:10px;background:#172a3d;color:#eaf2f8;border:1px solid var(--line);}
.stTextInput input,.stSelectbox div[data-baseweb="select"],.stTextArea textarea {background:#102236!important;color:#edf7ff!important;border-color:#29445b!important;border-radius:10px!important;}
[data-testid="stFileUploader"] {background:rgba(19,39,57,.7);border:1px dashed rgba(57,214,195,.45);border-radius:16px;padding:12px;}
[data-testid="stTabs"] button {color:#a9bdcd!important;font-weight:700;}
[data-testid="stTabs"] button[aria-selected="true"] {color:#45dfcc!important;border-bottom-color:#39d6c3!important;}
hr {border-color:var(--line)!important;}
div[data-testid="stAlert"] {border-radius:13px;}
div[data-testid="stExpander"] {border:1px solid var(--line);border-radius:12px;background:rgba(16,31,46,.65);}
section[data-testid="stSidebar"] .stRadio label {padding:7px 4px;}
.smallcaps {text-transform:uppercase;letter-spacing:.13em;color:#7f9ab0;font-size:.69rem;font-weight:800;}
.hero {padding:25px 28px;border:1px solid rgba(87,211,202,.2);border-radius:22px;background:linear-gradient(110deg,rgba(17,48,67,.96),rgba(15,64,70,.83)),radial-gradient(circle at 85% 20%,rgba(57,214,195,.22),transparent 30%);box-shadow:0 18px 50px rgba(0,0,0,.18);margin-bottom:22px;}
.hero-title {font-family:'Manrope',sans-serif;font-size:2rem;font-weight:800;letter-spacing:-.055em;color:#f3fbff;line-height:1.12;}
.hero-sub {color:#b4cbd5;margin-top:8px;font-size:.96rem;}
.pill {display:inline-block;padding:5px 10px;border-radius:999px;background:rgba(57,214,195,.12);border:1px solid rgba(57,214,195,.25);color:#70eadb;font-size:.72rem;font-weight:800;letter-spacing:.04em;}
.panel {background:linear-gradient(145deg,rgba(20,39,57,.94),rgba(14,29,44,.94));border:1px solid var(--line);border-radius:17px;padding:18px 20px;}
.panel-title {font-family:'Manrope',sans-serif;font-weight:800;color:#edf6fb;font-size:1.02rem;}
.panel-sub {color:#8fa6b8;font-size:.82rem;}
.big-number {font-family:'Manrope',sans-serif;font-weight:800;font-size:1.85rem;color:#f4fbff;letter-spacing:-.04em;}
.muted {color:#8fa6b8;}
.good {color:#48dfb2;font-weight:800;}
.warn {color:#ffc66e;font-weight:800;}
.bad {color:#ff8d91;font-weight:800;}
.footer {color:#71889a;font-size:.75rem;text-align:center;padding:22px 0 4px;}
div[data-testid="stDataFrame"] {border:1px solid var(--line);border-radius:12px;overflow:hidden;}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def dnum(v):
    if v is None: return None
    try:
        s = re.sub(r"[^\d.\-]", "", str(v).replace(",", ""))
        return Decimal(s) if s not in ("", "-", ".") else None
    except (InvalidOperation, ValueError):
        return None

def rs(v):
    n=dnum(v)
    return f"Rs. {n:,.0f}" if n is not None else "—"

def demo():
    return {
        "provider":"K-Electric (sample scenario)",
        "billing_period":"October 2026",
        "issue_date":"20 Oct 2026",
        "due_date":"05 Nov 2026",
        "consumer_category":"Residential",
        "meter_readings":{"previous":12100,"current":12450},
        "units_billed":350,
        "total_amount":12500,
        "currency":"PKR",
        "charges":[
            {"name":"Energy charges","amount":8200},
            {"name":"Fuel adjustment","amount":900},
            {"name":"Taxes & duties","amount":2400},
            {"name":"Other charges","amount":1000}
        ],
        "extraction_warnings":["Sample values for interface demonstration only. Not an actual customer bill."],
        "plain_language_summary":"Your sample bill shows 350 units consumed and a payable amount of Rs. 12,500. The figures are illustrative and should not be treated as an official tariff calculation.",
        "energy_saving_tips":[
            "Compare units consumed month to month, not only the payable amount.",
            "Switch off appliances that remain on standby when not needed.",
            "Use efficient lighting and maintain cooling equipment."
        ]
    }

def verify(data):
    checks=[]
    meter=data.get("meter_readings") or {}
    prev,cur,billed=dnum(meter.get("previous")),dnum(meter.get("current")),dnum(data.get("units_billed"))
    if prev is not None and cur is not None and billed is not None:
        calc=cur-prev
        ok=abs(calc-billed)<=Decimal("1")
        checks.append(("Meter reading difference","Consistent" if ok else "Review required",
                       f"{cur} − {prev} = {calc} units; bill shows {billed} units."))
    else:
        checks.append(("Meter reading difference","Insufficient data","Both meter readings and billed units are needed."))

    charges=data.get("charges") or []
    vals=[dnum(x.get("amount")) for x in charges if isinstance(x,dict)]
    total=dnum(data.get("total_amount"))
    if vals and total is not None and all(v is not None for v in vals):
        subtotal=sum(vals,Decimal("0"))
        ok=abs(subtotal-total)<=Decimal("2")
        checks.append(("Charge rows vs displayed total","Consistent" if ok else "Review required",
                       f"Extracted rows sum to {rs(subtotal)}; displayed total is {rs(total)}. This is only a partial check if credits, subtotals or adjustments are omitted."))
    else:
        checks.append(("Charge rows vs displayed total","Insufficient data","A total and sufficiently complete charge rows are required."))
    checks.append(("Due date","Found" if data.get("due_date") else "Not found",
                   str(data.get("due_date") or "No due date was confidently extracted.")))
    return checks

def gemini_extract(file, provider, language, key, model):
    client=genai.Client(api_key=key)
    schema={
        "provider":"string or null","billing_period":"string or null","issue_date":"string or null",
        "due_date":"string or null","consumer_category":"string or null",
        "meter_readings":{"previous":"number or null","current":"number or null"},
        "units_billed":"number or null","total_amount":"number or null","currency":"string",
        "charges":[{"name":"string","amount":"number or null"}],
        "extraction_warnings":["string"],"plain_language_summary":"string","energy_saving_tips":["string"]
    }
    prompt=f"""Carefully extract visible information from this Pakistani electricity bill.
Return ONLY valid JSON matching this schema: {json.dumps(schema)}
Requested provider hint: {provider}. Explanation language: {language}.
Never invent values. Use null for unknown numeric values. Preserve printed amounts exactly.
Distinguish meter readings from units consumed. Include visible charge rows only.
Do not declare fraud, illegality, overbilling or official correctness.
Mention blur, cropped text and ambiguous digits in extraction_warnings.
Do not assume a tariff. Clearly label any advice as general.
"""
    part=types.Part.from_bytes(data=file.getvalue(),mime_type=file.type or "application/octet-stream")
    resp=client.models.generate_content(
        model=model,contents=[prompt,part],
        config=types.GenerateContentConfig(response_mime_type="application/json",temperature=0.1)
    )
    raw=(resp.text or "").strip()
    raw=re.sub(r"^```(?:json)?\s*|\s*```$","",raw,flags=re.I)
    return json.loads(raw)

# ---------- Session ----------
if "bill" not in st.session_state: st.session_state.bill=None
if "history" not in st.session_state:
    st.session_state.history=pd.DataFrame({
        "Month":["May","Jun","Jul","Aug","Sep","Oct"],
        "Units":[280,310,295,390,330,350],
        "Amount":[8900,9700,9300,13900,10800,12500]
    })
if "active_page" not in st.session_state: st.session_state.active_page="Overview"

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## ⚡ BillSaathi")
    st.markdown('<span class="pill">AI POWERED • PAKISTAN</span>',unsafe_allow_html=True)
    st.write("")
    page=st.radio("WORKSPACE",["Overview","Analyze a bill","Usage insights","How it works"],label_visibility="visible")
    st.session_state.active_page=page
    st.divider()
    st.markdown('<div class="smallcaps">Analysis preferences</div>',unsafe_allow_html=True)
    provider=st.selectbox("Utility provider",["Auto-detect","K-Electric","IESCO","LESCO","MEPCO","FESCO","GEPCO","HESCO","PESCO","QESCO","Other"])
    language=st.selectbox("Report language",["English","Urdu"])
    with st.expander("AI configuration"):
        api_key=st.text_input("Gemini API key",value=os.getenv("GEMINI_API_KEY",""),type="password")
        model=st.text_input("Model",value=os.getenv("GEMINI_MODEL","gemini-2.5-flash"))
        st.caption("Keys are not saved to the source code. Add them as deployment secrets for production.")
    st.divider()
    st.markdown('<div class="smallcaps">Prototype status</div>',unsafe_allow_html=True)
    st.markdown("🟢 Interface ready")
    st.markdown("🟡 Provider tariff engine: not connected")
    st.markdown('<div class="footer">Independent prototype · Not a utility service</div>',unsafe_allow_html=True)

# ---------- Header ----------
st.markdown("""
<div class="hero">
  <div style="display:flex;justify-content:space-between;gap:18px;align-items:flex-start;flex-wrap:wrap">
    <div>
      <div class="smallcaps" style="color:#8de8dc">YOUR ENERGY, MADE CLEAR</div>
      <div class="hero-title">Take control of your<br>electricity bill.</div>
      <div class="hero-sub">Understand every charge. Check the numbers. Discover your usage patterns.</div>
    </div>
    <div style="text-align:right;min-width:125px">
      <div class="pill">BETA EXPERIENCE</div>
      <div style="font-size:2.4rem;margin-top:12px">⚡</div>
      <div style="color:#a9c7d1;font-size:.78rem">Smarter energy decisions</div>
    </div>
  </div>
</div>
""",unsafe_allow_html=True)

# ---------- Overview ----------
if page=="Overview":
    st.markdown("### Your energy snapshot")
    st.caption("A sample dashboard is shown until you analyze your own bill. Sample values are illustrative.")
    hist=st.session_state.history
    m1,m2,m3,m4=st.columns(4)
    m1.metric("Latest consumption",f"{hist.iloc[-1]['Units']} units","6.1% vs previous")
    m2.metric("Latest bill",rs(hist.iloc[-1]["Amount"]),"15.7% vs previous")
    m3.metric("6-month average",f"{hist['Units'].mean():.0f} units","Monthly")
    m4.metric("Bills analyzed",str(1 if st.session_state.bill else 0),"Current session")
    c1,c2=st.columns([1.55,1],gap="large")
    with c1:
        st.markdown('<div class="panel"><div class="panel-title">Consumption trend</div><div class="panel-sub">Illustrative six-month usage history</div></div>',unsafe_allow_html=True)
        fig=go.Figure()
        fig.add_trace(go.Bar(x=hist["Month"],y=hist["Units"],name="Units",marker_color="#2bc9b8",opacity=.88))
        fig.add_trace(go.Scatter(x=hist["Month"],y=hist["Units"],mode="lines+markers",name="Trend",line=dict(color="#e9c77b",width=2),marker=dict(size=6)))
        fig.update_layout(height=300,margin=dict(l=8,r=8,t=20,b=8),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#c6d5e1",legend=dict(orientation="h",y=1.12),yaxis_title="Units",xaxis_title="",yaxis=dict(gridcolor="rgba(180,200,220,.1)"),xaxis=dict(gridcolor="rgba(180,200,220,.05)"))
        st.plotly_chart(fig,use_container_width=True)
    with c2:
        st.markdown('<div class="panel"><div class="panel-title">Quick actions</div><div class="panel-sub">Start with your latest electricity bill</div></div>',unsafe_allow_html=True)
        st.write("")
        if st.button("＋  Analyze a new bill",use_container_width=True,type="primary"):
            st.session_state.active_page="Analyze a bill"
            st.rerun()
        if st.button("View usage insights",use_container_width=True):
            st.session_state.active_page="Usage insights"
            st.rerun()
        st.write("")
        st.info("Tip: Upload a clear image or PDF. Cover personal identifiers before uploading.")
        st.markdown('<div class="panel"><div class="smallcaps">Our promise</div><div style="font-size:1.1rem;font-weight:800;margin-top:8px">Evidence over guesswork.</div><div class="panel-sub" style="margin-top:6px">AI reads the document. Transparent code checks the arithmetic. You stay in control.</div></div>',unsafe_allow_html=True)
    st.markdown("### Built for clarity")
    x1,x2,x3=st.columns(3)
    x1.markdown('<div class="panel"><div style="font-size:1.5rem">🔎</div><b>Understand your bill</b><div class="panel-sub">Turn dense bill layouts into readable information.</div></div>',unsafe_allow_html=True)
    x2.markdown('<div class="panel"><div style="font-size:1.5rem">🧮</div><b>Check the arithmetic</b><div class="panel-sub">See which calculations match and which need review.</div></div>',unsafe_allow_html=True)
    x3.markdown('<div class="panel"><div style="font-size:1.5rem">📈</div><b>See usage patterns</b><div class="panel-sub">Compare monthly consumption and bill trends.</div></div>',unsafe_allow_html=True)

# ---------- Analyze ----------
elif page=="Analyze a bill":
    st.markdown("### Analyze your electricity bill")
    st.caption("Upload a document, extract the visible values, then review each verification result.")
    upcol,infocol=st.columns([1.35,.8],gap="large")
    with upcol:
        uploaded=st.file_uploader("Drop your bill here or browse files",type=["png","jpg","jpeg","webp","pdf"],label_visibility="collapsed")
        if uploaded:
            st.success(f"Ready to analyze · {uploaded.name} · {uploaded.size/1024:.1f} KB")
            if uploaded.type.startswith("image/"): st.image(uploaded,use_container_width=True)
        b1,b2=st.columns(2)
        with b1: run=st.button("✨  Analyze with AI",type="primary",use_container_width=True,disabled=(uploaded is None or not api_key.strip()))
        with b2: sample=st.button("Preview sample analysis",use_container_width=True)
        if uploaded and not api_key.strip():
            st.warning("Add your Gemini API key in the sidebar to analyze a real document.")
        if sample:
            st.session_state.bill=demo()
            st.success("Sample report loaded. All sample data is illustrative.")
        if run:
            try:
                with st.spinner("AI is reading your bill and structuring the information..."):
                    st.session_state.bill=gemini_extract(uploaded,provider,language,api_key.strip(),model.strip())
                st.success("Extraction complete. Please compare the results with your original bill.")
            except Exception as e:
                st.error(f"Could not analyze this document: {e}")
                st.caption("Check the API key, model availability, internet connection and document format.")
    with infocol:
        st.markdown('<div class="panel"><div class="panel-title">What you will get</div><br><div>01 &nbsp; <b>Structured bill details</b><div class="panel-sub">Provider, billing period, units, readings and charges.</div></div><hr><div>02 &nbsp; <b>Transparent checks</b><div class="panel-sub">Arithmetic checks with the evidence used.</div></div><hr><div>03 &nbsp; <b>Plain-language report</b><div class="panel-sub">Clear explanation and practical energy tips.</div></div></div>',unsafe_allow_html=True)
        st.write("")
        st.warning("Your bill contains personal information. Redact your name, address, account/reference number and barcode before uploading.")
    data=st.session_state.bill
    if data:
        st.divider()
        st.markdown("### Analysis report")
        q1,q2,q3,q4=st.columns(4)
        q1.metric("Units billed",str(data.get("units_billed") if data.get("units_billed") is not None else "—"))
        q2.metric("Total payable",rs(data.get("total_amount")))
        q3.metric("Due date",str(data.get("due_date") or "Not found"))
        q4.metric("Provider",str(data.get("provider") or "Unknown"))
        t1,t2,t3=st.tabs(["✓ Verification results","Bill details","AI explanation"])
        with t1:
            results=verify(data)
            for name,status,detail in results:
                if status=="Consistent" or status=="Found":
                    st.success(f"**{name} · {status}**\n\n{detail}")
                elif status=="Review required":
                    st.warning(f"**{name} · {status}**\n\n{detail}")
                else:
                    st.info(f"**{name} · {status}**\n\n{detail}")
            for warning in data.get("extraction_warnings") or []:
                st.caption("⚠️ "+str(warning))
        with t2:
            st.json(data)
            charges=data.get("charges") or []
            if charges:
                df=pd.DataFrame(charges)
                st.dataframe(df,use_container_width=True,hide_index=True)
                vals=pd.to_numeric(df["amount"],errors="coerce")
                if vals.notna().any():
                    fig=px.bar(df,x="name",y=vals,title="Extracted charge breakdown",labels={"name":"Charge","y":"Amount (PKR)"},color_discrete_sequence=["#39d6c3"])
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#dce8f1",margin=dict(l=5,r=5,t=45,b=5),yaxis=dict(gridcolor="rgba(180,200,220,.1)"))
                    st.plotly_chart(fig,use_container_width=True)
        with t3:
            st.markdown('<div class="panel"><div class="panel-title">In plain language</div></div>',unsafe_allow_html=True)
            st.write(data.get("plain_language_summary") or "No summary returned.")
            st.markdown("#### Practical energy tips")
            for tip in data.get("energy_saving_tips") or []: st.write("• "+str(tip))
        st.download_button("↓  Download report (JSON)",json.dumps(data,indent=2,ensure_ascii=False),file_name="billsaathi_report.json",mime="application/json")

# ---------- Insights ----------
elif page=="Usage insights":
    st.markdown("### Usage insights")
    st.caption("Illustrative history for the prototype. Real historical bill upload and account linking are not yet implemented.")
    hist=st.session_state.history.copy()
    a,b=st.columns(2)
    a.metric("Average monthly usage",f"{hist.Units.mean():.0f} units")
    b.metric("Highest usage month",f"{hist.loc[hist.Units.idxmax(),'Month']} · {hist.Units.max()} units")
    f1=px.area(hist,x="Month",y="Units",markers=True,title="Monthly electricity consumption",color_discrete_sequence=["#39d6c3"])
    f1.update_traces(fillcolor="rgba(57,214,195,.13)",line=dict(width=3))
    f1.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#dce8f1",yaxis=dict(gridcolor="rgba(180,200,220,.1)"))
    st.plotly_chart(f1,use_container_width=True)
    f2=px.bar(hist,x="Month",y="Amount",title="Monthly bill amount (illustrative)",color_discrete_sequence=["#e6bc72"])
    f2.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#dce8f1",yaxis=dict(gridcolor="rgba(180,200,220,.1)"))
    st.plotly_chart(f2,use_container_width=True)
    st.info("To make these insights personal, the next iteration will let users add several past bills and build a verified monthly history.")

# ---------- How it works ----------
else:
    st.markdown("### How BillSaathi works")
    st.caption("A transparent pipeline: AI extracts; deterministic code checks; the user makes the decision.")
    steps=[
        ("01","Document intake","The user uploads an electricity bill image or PDF."),
        ("02","Multimodal extraction","Gemini identifies visible fields and returns structured JSON. Missing values remain unknown."),
        ("03","Deterministic verification","Python checks meter-reading differences and selected arithmetic relationships."),
        ("04","Explainable report","The interface shows the evidence, limitations, warnings and practical next steps.")
    ]
    for num,title,desc in steps:
        st.markdown(f'<div class="panel" style="display:flex;gap:18px;margin-bottom:12px"><div style="font-size:1.3rem;color:#42d8c6;font-weight:800">{num}</div><div><div class="panel-title">{title}</div><div class="panel-sub">{desc}</div></div></div>',unsafe_allow_html=True)
    st.markdown("#### What this prototype does not claim")
    st.write("- It does not connect to utility billing systems.")
    st.write("- It does not yet validate official provider tariffs or taxes.")
    st.write("- It cannot prove fraud, overbilling or legal non-compliance.")
    st.write("- AI extraction can make mistakes; compare values with the original bill.")

st.markdown('<div class="footer">BillSaathi AI · Independent prototype · Built to make electricity bills easier to understand<br>Not affiliated with K-Electric, DISCOs, NEPRA or any government agency.</div>',unsafe_allow_html=True)
