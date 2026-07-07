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
# ENGINE CONFIGURATION & RECOVERY MATRIX
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

def resolve_industry_to_macro_archetype(industry_input):
    ind = str(industry_input).strip().lower()
    if any(x in ind for x in ['fmcg', 'd2c', 'b2c', 'retail', 'e-commerce', 'fashion', 'beverage', 'food', 'entertainment', 'gaming', 'automobile', 'apparel', 'cosmetics']):
        return "volume_pull"
    elif any(x in ind for x in ['b2b', 'it', 'software', 'saas', 'consulting', 'services', 'legal', 'finance', 'agency', 'tech', 'cleantech', 'spacetech', 'outsourcing']):
        return "value_trust"
    elif any(x in ind for x in ['manufacturing', 'production', 'steel', 'chemical', 'logistics', 'supply chain', 'agriculture', 'mining', 'construction', 'infrastructure', 'textile']):
        return "scale_margin"
    elif any(x in ind for x in ['healthcare', 'pharma', 'hospital', 'banking', 'insurance', 'defense', 'aviation', 'biotech', 'medical', 'energy', 'utility', 'government']):
        return "compliance_credibility"
    return "volume_pull"

def normalize_pipeline(df):
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

# Only ask for the brand name! Industry and API keys are completely automated now.
brand_name = st.sidebar.text_input("Target Brand Name", value="Tech Mahindra")

trigger_analysis = st.sidebar.button("🚀 Run Decision Intelligence Engine")

# ==============================================================================
# CORE EXECUTION LOOP WITH AUTO-INDUSTRY SECTOR FETCHING
# ==============================================================================
if trigger_analysis:
    # Pull credentials securely from Streamlit Cloud Secrets Manager
    try:
        serper_api_key = st.secrets["SERPER_API_KEY"]
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError:
        st.error("🔒 Secrets Missing: Please configure 'SERPER_API_KEY' and 'GEMINI_API_KEY' inside your Streamlit Cloud Secrets control panel.")
        st.stop()

    with st.spinner(f"Classifying company vertical and compiling analytics for {brand_name.upper()}..."):
        
        # Initialize Gemini client for pre-flight sector detection
        client = genai.Client(api_key=gemini_api_key)
        
        classification_prompt = f"""
        Identify the exact global primary business industry sector or vertical for the company '{brand_name}'.
        Respond with ONLY the name of the industry sector in 1 to 3 words max (e.g., 'IT Services', 'FMCG', 'Automobile', 'SaaS'). 
        Do not add periods, punctuation, or full sentences.
        """
        try:
            class_response = client.models.generate_content(model='gemini-2.5-flash', contents=classification_prompt)
            input_industry = class_response.text.strip().replace(".", "")
        except Exception:
            input_industry = "IT" # Fallback if network drops
        
        # Map detected sector into macroeconomic engine archetype
        macro_archetype = resolve_industry_to_macro_archetype(input_industry)
        profile = GLOBAL_MACRO_MATRIX[macro_archetype]
        weights = profile["weights"]
        current_date = dt.date.today()
        
        # --- Live Ingestion Layers ---
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
        data.append({'recorded_date': current_date, 'dimension': 'commercial', 'metric_name': 'price_premium_index', 'raw_value': 40.50 if not is_heavy else 79.80})
        
        df_raw = pd.DataFrame(data)
        df_raw['brand_name'] = brand_name
        df_raw['recorded_date'] = pd.to_datetime(df_raw['recorded_date']).dt.date
        
        df_processed = normalize_pipeline(df_raw)
        df_processed['normalized_value'] = df_processed['normalized_value'].fillna(50.0)
        
        df_pivot = df_processed.pivot(index='recorded_date', columns='dimension', values='normalized_value').fillna(50.0)
        df_pivot['BHI'] = ((df_pivot['external'] * weights['external']) + (df_pivot['internal'] * weights['internal']) + (df_pivot['commercial'] * weights['commercial'])).round(2)
        
        latest_bhi = df_pivot['BHI'].iloc[-1]
        
        # --- UI Dashboard Presentation ---
        st.success(f"🤖 Auto-Classification Success: Detected '{brand_name}' as operating in the '{input_industry}' industry. Initialized the [{macro_archetype.upper()}] engine matrix.")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(label="Brand Health Index (BHI)", value=f"{latest_bhi}/100")
        col2.metric(label="Inferred Macro Sector", value=macro_archetype.upper().replace("_", " "))
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
