import streamlit as st
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
from src.agent.sql_agent import SQLAgent

# --- Page Configuration ---
st.set_page_config(
    page_title="Lumina - Dubai Real Estate AI",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS (Rich Money / Fintech Aesthetic) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }

    /* Ultra-dark obsidian background */
    .stApp {
        background-color: #050507;
        color: #F8FAFC;
    }
    
    /* --- Layout Columns --- */
    
    /* Left column (Brand/Value Prop) */
    [data-testid="column"]:nth-of-type(1) {
        background: rgba(8, 8, 10, 0.85);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        padding: 3rem 2.5rem;
        border-right: 1px solid rgba(212, 175, 55, 0.15); /* Subtle gold border */
        box-shadow: inset -15px 0 30px rgba(0, 0, 0, 0.4);
        height: 100vh;
    }
    
    /* Right column (Chat Area) */
    [data-testid="column"]:nth-of-type(2) {
        padding: 2rem 4rem;
        background-image: 
            radial-gradient(at 0% 0%, rgba(212, 175, 55, 0.05) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.05) 0px, transparent 50%);
    }

    /* --- Typography & Contrast --- */
    h1, h2, h3, h4, h5, h6 { 
        color: #FFFFFF !important; 
        font-weight: 600 !important;
        letter-spacing: -0.02em;
    }
    
    p, span, div { 
        color: #E2E8F0 !important; 
        line-height: 1.6 !important;
    }
    
    /* Highlight color (Gold) */
    strong {
        color: #D4AF37 !important;
        font-weight: 600 !important;
    }

    /* --- Chat Input Container --- */
    .stChatInputContainer {
        padding-bottom: 2rem;
    }
    
    [data-testid="stChatInput"] {
        border-radius: 12px !important;
        background-color: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(212, 175, 55, 0.3) !important; /* Gold border */
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5) !important;
        transition: all 0.3s ease;
    }
    
    [data-testid="stChatInput"]:focus-within {
        border-color: #D4AF37 !important;
        background-color: rgba(212, 175, 55, 0.05) !important;
        box-shadow: 0 8px 32px rgba(212, 175, 55, 0.1) !important;
    }
    
    /* Input text color and transparent background overrides */
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] div[data-baseweb="textarea"],
    [data-testid="stChatInput"] div[data-baseweb="base-input"],
    [data-testid="stChatInput"] div {
        background-color: transparent !important;
    }

    [data-testid="stChatInput"] textarea {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        caret-color: #D4AF37 !important;
    }
    
    [data-testid="stChatInput"] textarea::placeholder {
        color: #64748B !important;
        -webkit-text-fill-color: #64748B !important;
    }

    /* --- Buttons --- */
    .stButton > button {
        background: rgba(20, 20, 22, 0.8);
        border: 1px solid rgba(212, 175, 55, 0.2);
        border-radius: 8px;
        color: #F8FAFC !important;
        font-weight: 500;
        padding: 0.75rem 1rem;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        text-align: left !important;
        display: flex;
        justify-content: flex-start;
        align-items: center;
    }
    
    .stButton > button p {
        color: #F8FAFC !important;
        margin: 0 !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        background: rgba(212, 175, 55, 0.1);
        border-color: rgba(212, 175, 55, 0.5);
        box-shadow: 0 4px 12px rgba(212, 175, 55, 0.15);
    }

    /* --- Chat Messages --- */
    [data-testid="stChatMessage"] {
        background: rgba(20, 20, 22, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 1.5rem !important;
        margin-bottom: 1.5rem !important;
    }
    
    [data-testid="chatAvatarIcon-user"] {
        background-color: #3b82f6 !important;
    }
    
    [data-testid="chatAvatarIcon-assistant"] {
        background-color: #D4AF37 !important; /* Gold assistant */
        color: #000000 !important;
    }

    /* --- Badges --- */
    .dld-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        border-radius: 4px;
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #10B981;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 2rem;
    }
    
    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10B981;
        box-shadow: 0 0 10px #10B981;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: .4; }
    }
    
    /* Remove top margin */
    .block-container {
        padding-top: 4rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Initialize Backend Agent ---
@st.cache_resource
def get_agent():
    return SQLAgent()

agent = get_agent()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Welcome to Lumina AI. I provide institutional-grade analysis on the Dubai Real Estate market."}
    ]
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Plotly Theme & Layout ---
def get_plotly_layout():
    return go.Layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter", color="#E2E8F0"),
        xaxis=dict(showgrid=False, zeroline=False, color="#94A3B8"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False, color="#94A3B8"),
        margin=dict(l=0, r=0, t=20, b=0),
        hovermode="x unified",
        colorway=["#D4AF37", "#10B981", "#3B82F6", "#F43F5E"] # Gold, Emerald, Blue, Rose
    )

def render_kpi_metrics(df: pd.DataFrame):
    """Renders high-end KPI metrics from the DataFrame."""
    if df is None or df.empty:
        return
    
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    if not num_cols:
        return
        
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns(min(len(num_cols), 3))
    
    for i, col in enumerate(num_cols[:3]):
        # Simple aggregation: mean for averages/rates, sum for totals
        val = df[col].mean() if any(x in col.lower() for x in ['avg', 'rate', 'roi', 'price']) else df[col].sum()
        
        # Financial formatting
        if val >= 1_000_000:
            formatted_val = f"{val/1_000_000:.2f}M"
        elif val >= 1_000:
            formatted_val = f"{val/1_000:.1f}K"
        elif 0 < val < 100: # Probably a percentage like ROI
            formatted_val = f"{val:.1f}%" if 'roi' in col.lower() or 'rate' in col.lower() else f"{val:.2f}"
        else:
            formatted_val = f"{val:,.0f}"
            
        with cols[i]:
            st.markdown(f"""
            <div style="background: rgba(20, 20, 22, 0.8); border-left: 3px solid #D4AF37; 
                        border-radius: 4px; padding: 1.5rem; 
                        box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
                <p style="color: #94A3B8; font-size: 0.75rem; text-transform: uppercase; font-weight: 600; letter-spacing: 1px; margin-bottom: 0.5rem;">{col.replace('_', ' ').title()}</p>
                <h2 style="color: #F8FAFC; margin: 0; font-size: 2.2rem; font-weight: 300;">{formatted_val}</h2>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

def render_dynamic_chart(df: pd.DataFrame):
    """Renders a highly styled Plotly chart."""
    if df is None or df.empty or len(df.columns) < 2:
        return

    string_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
    num_cols = df.select_dtypes(include=['number']).columns.tolist()

    if not num_cols: return
    
    fig = None

    if string_cols and num_cols:
        index_col = string_cols[0]
        y_col = num_cols[0]
        
        # Time-series -> Area Chart
        if any(x in index_col.lower() for x in ['year', 'month', 'date', 'quarter']):
            fig = px.area(df, x=index_col, y=y_col, markers=True)
            fig.update_traces(line_color='#D4AF37', fillcolor='rgba(212, 175, 55, 0.15)')
        
        # Categorical -> Horizontal Bar Chart
        else:
            df_sorted = df.sort_values(by=y_col, ascending=True).tail(10) # Top 10 max
            fig = px.bar(df_sorted, x=y_col, y=index_col, orientation='h')
            fig.update_traces(marker_color='#10B981', marker_line_color='rgba(16, 185, 129, 0.5)', marker_line_width=1)
            
    elif len(num_cols) >= 2:
        # Numeric vs Numeric -> Line Chart
        fig = px.line(df, x=num_cols[0], y=num_cols[1], markers=True)
        fig.update_traces(line_color='#D4AF37')

    if fig:
        fig.update_layout(get_plotly_layout())
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- Layout ---
col1, col2 = st.columns([1, 2.5]) # Widened the chat area slightly for charts

# --- Left Column: Brand & Value Prop ---
with col1:
    st.markdown("###  Lumina AI")
    
    st.markdown("""
        <div class="dld-badge">
            <div class="pulse-dot"></div>
            DLD Live Feed
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<h2 style='font-size: 2.5rem; font-weight: 300; line-height: 1.2;'>Precision Intelligence for Dubai Real Estate.</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style='margin-top: 1.5rem; padding: 1.25rem; background: rgba(255,255,255,0.02); border-left: 2px solid #D4AF37; border-radius: 4px;'>
        <p style='color: #E2E8F0 !important; font-size: 0.95rem; margin-bottom: 0.5rem;'><strong>What is Lumina?</strong></p>
        <p style='color: #94A3B8 !important; font-size: 0.85rem; line-height: 1.5;'>
            Lumina is an autonomous AI agent built for real estate investors. It instantly translates natural language questions into complex SQL queries, running them directly against a proprietary data warehouse of over 1 Million official Dubai Land Department (DLD) transactions.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br><p style='color: #D4AF37 !important; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px;'>Example Queries to Try</p>", unsafe_allow_html=True)
    
    st.markdown("""
    <ul style='color: #94A3B8; font-size: 0.85rem; line-height: 1.6;'>
        <li><em>"Which 3 communities offer the highest ROI for a 2-bedroom apartment under 2 Million AED?"</em></li>
        <li><em>"Show me the price trend for villas in Arabian Ranches over the last 5 years."</em></li>
    </ul>
    """, unsafe_allow_html=True)
    
    if st.button("⚡ Run ROI Analysis Example", use_container_width=True):
        st.session_state.prompt_suggestion = "Where are the top 5 communities in Dubai for the highest ROI on 1-bedroom apartments?"

# --- Right Column: Chat Interface & Analytics ---
with col2:
    # Create a container for messages to keep them above the input box
    chat_placeholder = st.container()
    
    # Get prompt suggestion if any
    prompt_suggestion = None
    if getattr(st.session_state, 'prompt_suggestion', None):
        prompt_suggestion = st.session_state.prompt_suggestion
        del st.session_state.prompt_suggestion

    # Render the chat input box at the bottom of the column
    prompt = st.chat_input("Query the market...")
    if prompt_suggestion:
        prompt = prompt_suggestion

    # Render existing messages inside the placeholder container
    with chat_placeholder:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                if "raw_df" in message and message["raw_df"] is not None:
                    df = message["raw_df"]
                    render_kpi_metrics(df)
                    render_dynamic_chart(df)

    # Process new query and inject it inside the container dynamically
    if prompt:
        # Append to visual messages list
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with chat_placeholder:
            # Render user query immediately above the input box
            with st.chat_message("user"):
                st.markdown(prompt)
                
            # Render assistant answer
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                with st.spinner('Synthesizing DLD data...'):
                    # Pass the hidden brain state (chat_history) to the agent
                    report, df = agent.ask(prompt, chat_history=st.session_state.chat_history)
                    
                    message_placeholder.markdown(report)
                    render_kpi_metrics(df)
                    render_dynamic_chart(df)
                    
        # Append response to messages list for persistence
        st.session_state.messages.append({
            "role": "assistant", 
            "content": report, 
            "raw_df": df
        })
        
        # Save to brain state memory
        st.session_state.chat_history.append(("user", prompt))
        st.session_state.chat_history.append(("assistant", report))
        
        # Rerun to sync everything
        st.rerun()
