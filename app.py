import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import httpx
from datetime import datetime, timedelta

# --- 1. INITIAL CONFIG (MUST BE FIRST) ---
st.set_page_config(page_title="MaintainIQ Commander", layout="wide", page_icon="🏭")

# --- 2. LANGCHAIN & AI SETUP (SAFE INITIALIZATION) ---
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# We wrap this so a connection failure doesn't crash the UI
@st.cache_resource
def get_llm():
    try:
        return ChatOpenAI(
            base_url="https://genailab.tcs.in",
            model="azure_ai/genailab-maas-DeepSeek-V3-0324",
            api_key="sk-yBlBuv8OtSuTbnRNusXZkw", 
            http_client=httpx.Client(verify=False),
            streaming=True
        )
    except:
        return None

llm = get_llm()

# --- 3. CUSTOM CSS (STABLE VERSION) ---
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    [data-testid="stSidebar"] { background-color: #0B1120 !important; }
    [data-testid="stMetric"] {
        background: white; border-radius: 15px; padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 4px solid #3B82F6;
    }
    .stButton>button {
        background: linear-gradient(135deg, #2563EB, #1D4ED8);
        color: white; border-radius: 8px; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. DATA ENGINE ---
if 'machines_data' not in st.session_state:
    st.session_state.machines_data = pd.DataFrame([
        {"id":"M01", "name":"Alpha Compressor", "type":"compressor", "location":"Zone A", "age":4.2, "hoursUsed":8420, "lastService":58, "usageIntensity":0.92, "past_failures": 2},
        {"id":"M02", "name":"Beta Pump Station", "type":"pump", "location":"Zone A", "age":2.1, "hoursUsed":4100, "lastService":12, "usageIntensity":0.65, "past_failures": 0},
        {"id":"M03", "name":"Conveyor Line 1", "type":"conveyor", "location":"Zone B", "age":6.8, "hoursUsed":12300, "lastService":89, "usageIntensity":0.88, "past_failures": 1},
        {"id":"M04", "name":"Turbine Unit T1", "type":"turbine", "location":"Zone C", "age":3.5, "hoursUsed":6800, "lastService":34, "usageIntensity":0.74, "past_failures": 0},
        {"id":"M05", "name":"Hydraulic Press P1", "type":"press", "location":"Zone B", "age":5.1, "hoursUsed":9200, "lastService":120, "usageIntensity":0.98, "past_failures": 4},
    ])

def process_data():
    df = st.session_state.machines_data.copy()
    # Simple weighted risk formula
    df['Risk Score'] = ((df['lastService']/500 * 40) + (df['usageIntensity'] * 30) + (df['past_failures'] * 10)).clip(0, 100).astype(int)
    df['Tier'] = df['Risk Score'].apply(lambda x: "Critical" if x >= 75 else "Warning" if x >= 50 else "Healthy")
    df['Cost of Delay ($/day)'] = (df['Risk Score'] * 25).astype(int)
    df['Rec. Date'] = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    return df

df = process_data()

# --- 5. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color:white; text-align:center;'>⚙️ MaintainIQ</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#60A5FA; text-align:center;'>v5 Commander</p>", unsafe_allow_html=True)
    st.write("---")
    menu = st.radio("Go to:", ["🏭 Command Center", "📋 Priority Queue", "📂 Data Hub", "🤖 AI Advisor"])
    st.write("---")
    st.info("💡 AI Active")

# --- 6. VIEWS ---
if menu == "🏭 Command Center":
    st.title("Facility Health Dashboard")
    
    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Critical", len(df[df['Tier']=="Critical"]))
    m2.metric("Warnings", len(df[df['Tier']=="Warning"]))
    m3.metric("Fleet Risk", f"{int(df['Risk Score'].mean())}%")
    m4.metric("Daily Risk", f"${df['Cost of Delay ($/day)'].sum():,}")

    col_map, col_list = st.columns([2, 1])
    with col_map:
        st.subheader("Equipment Risk Map")
        fig = px.treemap(df, path=['Tier', 'location', 'name'], values='Cost of Delay ($/day)', 
                         color='Risk Score', color_continuous_scale='RdYlGn_r')
        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with col_list:
        st.subheader("Top Actions")
        if st.button("🚨 Inject Anomaly"):
            idx = np.random.randint(0, len(st.session_state.machines_data))
            st.session_state.machines_data.at[idx, 'usageIntensity'] = 1.0
            st.session_state.machines_data.at[idx, 'lastService'] += 100
            st.rerun()
        st.dataframe(df[['id', 'name', 'Tier']].head(5), hide_index=True)

elif menu == "📋 Priority Queue":
    st.title("Priority Maintenance Schedule")
    st.data_editor(df[['id', 'name', 'Tier', 'Risk Score', 'Cost of Delay ($/day)', 'Rec. Date']], 
                   use_container_width=True, hide_index=True)
    if st.button("💾 Save Schedule"): st.success("Database Updated!")

elif menu == "📂 Data Hub":
    st.title("Data Ingestion")
    file = st.file_uploader("Upload CSV", type="csv")
    if file:
        st.session_state.machines_data = pd.read_csv(file)
        st.success("Uploaded!")
        st.rerun()
    st.subheader("Current Fleet Data")
    st.dataframe(st.session_state.machines_data, use_container_width=True)

elif menu == "🤖 AI Advisor":
    st.title("AI Maintenance Advisor")
    
    if llm is None:
        st.error("AI Connection Offline. Please check your API Key.")
    else:
        # Context for AI
        context = df[['id', 'name', 'Tier', 'Risk Score', 'Cost of Delay ($/day)']].to_markdown()
        sys_msg = f"You are a factory AI. Fleet Data:\n{context}\nAnswer concisely based ONLY on this data."

        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "I am analyzed your data. How can I help?"}]

        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.markdown(m["content"])

        if prompt := st.chat_input("Ask about machine risks..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant"):
                history = [SystemMessage(content=sys_msg)] + [
                    HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"]) 
                    for m in st.session_state.messages
                ]
                response = st.write_stream((chunk.content for chunk in llm.stream(history)))
                st.session_state.messages.append({"role": "assistant", "content": response})