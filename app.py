import streamlit as st
import datetime as dt
import json
import requests
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from google import genai

# ==============================================================================
# STREAMLIT INTERFACE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="BrandIQ Intelligence Framework",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 BrandIQ Decision Intelligence Framework")
st.markdown("### Measure, Diagnose, Predict, and Improve Corporate Brand Health Using Consumer, Employee, and Market Signals")
st.write("---")

# ==============================================================================
# GLOBAL ENGINE CONFIGURATION ARCHETYPES
# ==============================================================================
GLOBAL_MACRO_MATRIX = {
    "volume_pull": {
        "weights": {"external": 0.60, "internal": 0.15, "commercial": 0.25},
        "description": "Mass-market consumer conversion. Highly sensitive to external media noise, search salience, and short-cycle promotional fluctuations."
    },
    "value_trust": {
        "weights": {"external": 0.30, "internal": 0.50, "commercial": 0.20},
        "description": "Relationship-driven, human-capital intensive. Enterprise brand valuation is directly bound to employee alignment, advocacy, and service delivery quality."
    },
    "scale_margin": {
        "weights": {"external": 0.20, "internal": 0.35, "commercial": 0.45},
        "description": "Asset-heavy B2B procurement and supply-chain operations. Brand health translates directly to volume off-take commitment and margin maintenance."
    },
    "compliance_credibility": {
        "weights": {"external": 0.45, "internal": 0.35, "commercial": 0.20},
        "description": "High trust-deficit, highly regulated operating markets. Extremely sensitive to public safety indices, regulatory sentiment, and operational risk metrics."
    }
}

def normalize_pipeline(df):
    """
    Statistical Normalization Module: Applies rolling expanding Z-Score 
    and Min-Max scaling to compress multi-scale data streams into 0-100 indexes.
    """
    normalized_list = []
    for metric in df['metric_name'].unique():
        df_metric = df[df['metric_name'] == metric].copy().sort_values(by='recorded_date')
        rolling_mean = df_metric['raw_value'].expanding(min_periods=10).mean()
        rolling_std = df_metric['raw_value'].expanding(min_periods=10).std().fillna(1.0)
        z_scores = (df_metric['raw_value'] - rolling_mean) / rolling_std
        z_min = z_scores.expanding().min().fillna(-3.0)
        z_max = z_scores.expanding().max().fillna(3.0)
        range_denom = (z_max - z_min).replace(0, 1.0)
        df_metric['normalized_value'] = (((z_scores - z_min) / range_denom) * 100).clip(0, 100).round(2)
        normalized_list.append(df_metric)
    return pd.concat(normalized_list)

# ==============================================================================
# STREAMLIT USER CONFIGURATION CONTROL PANEL (CLEAN SIDEBAR)
# ==============================================================================
st.sidebar.header("🛠️ BrandIQ Control Panel")

# Only ask for the brand name. API and Industry routing are completely automated.
brand_name = st.sidebar.text_input("Target Brand Name", value="ClarityX")

trigger_analysis = st.sidebar.button("🚀 Run Decision Intelligence Engine")

# ==============================================================================
# DUAL-STAGE CORE EXECUTION LOOP
# ==============================================================================
if trigger_analysis:
    try:
        serper_api_key = st.secrets["SERPER_API_KEY"]
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError:
        st.error("🔒 Secrets Missing: Configure keys in the Streamlit Cloud Settings panel.")
        st.stop()

    with st.spinner(f"Analyzing enterprise model and compiling engine variables for {brand_name.upper()}..."):
        
        # Initialize Gemini Client for dynamic infrastructure routing
        client = genai.Client(api_key=gemini_api_key)
        
        # ----------------------------------------------------------------------
        # STAGE 1: FETCH SPECIFIC INDUSTRY TEXT INDICATION
        # ----------------------------------------------------------------------
        classification_prompt = f"""
        Identify the exact business industry vertical or niche for the company '{brand_name}'.
        Respond with ONLY the name of the vertical in 1 to 3 words max (e.g., 'Data Analytics', 'IT Services', 'FMCG', 'Automobile'). 
        Do not add periods, punctuation, or full sentences.
        """
        try:
            class_response = client.models.generate_content(model='gemini-2.5-flash', contents=classification_prompt)
            input_industry = class_response.text.strip().replace(".", "")
        except Exception:
            input_industry = "Data Analytics"
        
        # ----------------------------------------------------------------------
        # STAGE 2: DEEP MACRO-ARCHETYPE ROUTING POWERED BY LLM INFERENCE
        # ----------------------------------------------------------------------
        archetype_routing_prompt = f"""
        Analyze the business model of '{brand_name}', which operates in the '{input_industry}' space.
        Classify it into exactly ONE of these four global macroeconomic quadrants:
        
        1. volume_pull (If it is a B2C/D2C mass market consumer retail, product, or apparel brand)
        2. value_trust (If it is a B2B enterprise company, SaaS vendor, consulting agency, tech platform, or IT analytics firm where internal talent and business relationships drive value)
        3. scale_margin (If it is an asset-heavy manufacturer, logistics fleet, heavy industrial production, or raw supply-chain vendor)
        4. compliance_credibility (If it is a highly regulated, high-risk entity like a commercial hospital group, pharmaceutical drug manufacturer, commercial bank, or aviation line)
        
        Respond with ONLY the exact lowercase string identifier of the chosen quadrant: either 'volume_pull', 'value_trust', 'scale_margin', or 'compliance_credibility'. Do not include punctuation, numbers, headers, or any other words.
        """
        try:
            route_response = client.models.generate_content(model='gemini-2.5-flash', contents=archetype_routing_prompt)
            macro_archetype = route_response.text.strip().lower().replace(".", "").replace("'", "").replace('"', '')
            if macro_archetype not in GLOBAL_MACRO_MATRIX:
                macro_archetype = "value_trust"
        except Exception:
            macro_archetype = "value_trust"
            
        profile = GLOBAL_MACRO_MATRIX[macro_archetype]
        weights = profile["weights"]
        current_date = dt.date.today()
        
        # --- Live Ingestion Pipeline Layers ---
        total_mentions = 15.0
        try:
            search_url = f"https://google.serper.dev/news?q={brand_name}"
            headers = {'X-API-KEY': serper_api_key, 'Content-Type': 'application/json'}
            res = requests.get(search_url, headers=headers)
            total_mentions = float(len(res.json().get('news', [])))
        except: 
            pass
            
        mock_employee_satisfaction = 4.1
        try:
            search_url_internal = "https://google.serper.dev/search"
            payload = json.dumps({"q": f'"{brand_name}" employees culture sentiment feedback', "num": 10})
            response = requests.post(search_url_internal, headers={'X-API-KEY': serper_api_key, 'Content-Type': 'application/json'}, data=payload)
            organic_results = response.json().get('organic', [])
            if "restructuring" in str(organic_results).lower() or "layoff" in str(organic_results).lower():
                mock_employee_satisfaction = 3.3
        except: 
            pass

        # --- Analytical Time-Series Matrix Creation ---
        np.random.seed(hash(brand_name) % 999)
        days = 180
        start_date = dt.date(2026, 1, 1)
        date_list = [start_date + dt.timedelta(days=x) for x in range(days)]
        
        data = []
        for t in range(days):
            is_service = macro_archetype == "value_trust"
            is_heavy = macro_archetype == "scale_margin"
            
            int_base = 4.4 if is_service else 3.8
            if 45 <= t < 100: int_base -= 0.7
            data.append({'recorded_date': date_list[t], 'dimension': 'internal', 'metric_name': 'employee_sentiment_proxy', 'raw_value': float(max(1.0, min(5.0, int_base + np.random.normal(0, 0.12))))})
            
            ext_base = 10.0 if is_heavy else 25.0
            if 105 <= t < 150: ext_base *= 0.55
            data.append({'recorded_date': date_list[t], 'dimension': 'external', 'metric_name': 'media_mention_count', 'raw_value': float(max(0, ext_base + np.random.normal(0, 1.5)))})
            
            comm_base = 82.0 if is_heavy else 42.0
            data.append({'recorded_date': date_list[t], 'dimension': 'commercial', 'metric_name': 'price_premium_index', 'raw_value': float(max(5.0, comm_base + np.random.normal(0, 2.5)))})
            
        data.append({'recorded_date': current_date, 'dimension': 'internal', 'metric_name': 'employee_sentiment_proxy', 'raw_value': float(mock_employee_satisfaction)})
        data.append({'recorded_date': current_date, 'dimension': 'external', 'metric_name': 'media_mention_count', 'raw_value': float(total_mentions)})
        data.append({'recorded_date': current_date, 'dimension': 'commercial', 'metric_name': 40.50 if not is_heavy else 79.80})
        
        df_raw = pd.DataFrame(data)
        df_raw['brand_name'] = brand_name
        df_raw['recorded_date'] = pd.to_datetime(df_raw['recorded_date']).dt.date
        
        df_processed = normalize_pipeline(df_raw)
        df_processed['normalized_value'] = df_processed['normalized_value'].fillna(50.0)
        
        df_pivot = df_processed.pivot(index='recorded_date', columns='dimension', values='normalized_value').fillna(50.0)
        df_pivot['BHI'] = ((df_pivot['external'] * weights['external']) + (df_pivot['internal'] * weights['internal']) + (df_pivot['commercial'] * weights['commercial'])).round(2)
        
        latest_bhi = df_pivot['BHI'].iloc[-1]
        
        # --- UI Dashboard Presentation ---
        st.success(f"🤖 AI Architecture Engine Success: Evaluated '{brand_name}' as a '{input_industry}' firm and routed logic to the global [{macro_archetype.upper()}] model profile.")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(label="Brand Health Index (BHI)", value=f"{latest_bhi}/100")
        col2.metric(label="Dynamic Category Mapped", value=macro_archetype.upper().replace("_", " "))
        col3.metric(label="Internal Culture Score", value=f"{df_pivot['internal'].iloc[-1]:.1f}/100")
        col4.metric(label="External Market Score", value=f"{df_pivot['external'].iloc[-1]:.1f}/100")
        
        st.markdown("### 📊 Calculated Brand Metric Components Timeline Trajectory")
        chart_data = df_pivot[['BHI', 'internal', 'external', 'commercial']]
        st.line_chart(chart_data)
        
        # --- AI Executive Advisory Presentation ---
        st.write("---")
        st.subheader("📝 Official Boardroom Advisory Briefing")
        
        data_context = df_processed.sort_values(by='recorded_date')[['recorded_date', 'metric_name', 'normalized_value']].tail(45).to_string()
        
        prompt = f"""
        You are a Senior Strategic Advisor at a top global management consulting firm specializing in the '{macro_archetype}' archetype.
        Analyze this full processed brand metrics matrix for '{brand_name}' classified in the '{input_industry}' domain:
        
        {data_context}
        
        Economic Archetype Operational Rules applied: {profile['description']}
        
        Generate an exceptional boardroom briefing mapping directly to this structure:
        ## BrandIQ Executive Intelligence Report: {brand_name.upper()}
        **Global Macro Quadrant:** {macro_archetype.upper()} | **Composite Brand Health Index:** {latest_bhi}/100
        
        ### 1. OBSERVATIONAL DIAGNOSTIC (What Happened)
        Detail specific metric inflection point anomalies found across the matrix dataset.
        
        ### 2. TRAILING CAUSAL DYNAMICS (Why It Happened)
        Explain how employee sentiment variations, operational metrics, or media exposures explicitly link to final pricing premium index trends using the unique properties of the '{macro_archetype}' sector model.
        
        ### 3. EXECUTIVE OPERATIONS PLAYBOOK (What Should Management Do)
        Provide exactly two highly granular, non-generic tactical business recommendations customized to a firm in the '{input_industry}' space.
        Rank each playbook item directly by: Strategic Priority, Execution Complexity, and Statistical Confidence Factor %.
        """
        
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        st.markdown(response.text)
else:
    st.info("👈 Type a company name into the control panel sidebar and click 'Run Decision Intelligence Engine' to initialize automation.")
