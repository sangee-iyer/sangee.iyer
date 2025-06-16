import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
import os
from io import BytesIO
from PIL import Image
import re

st.set_page_config(page_title="SSA Performance Dashboard", layout="wide")
st.title("SSA Performance & Consultation Dashboard")

# --- File paths ---
main_file = "Live Resolution in Beacon - Release dashboard_Granular ticket data_Table.csv"
feedback_file = "Live Resolution in Beacon - Release dashboard_SSA feedback_Table - Sheet2.csv"
chat_file = "Support Official_ Support Unified Report_Chats_Table - Sheet1.csv"
overview_file = "Support Official_ Support Unified Report_Overview_Table - Total.csv"

# --- Helper: Load large CSV in chunks and concat ---
def load_large_csv(file, nrows=None):
    chunks = []
    for chunk in pd.read_csv(file, chunksize=100_000, nrows=nrows):
        chunks.append(chunk)
    return pd.concat(chunks, ignore_index=True)

# --- Helper: Extract collaboration quality from feedback file ---
def extract_collab_quality(df_feedback):
    # Find the row where 'collaboration_quality' appears
    idx = df_feedback[df_feedback.apply(lambda row: row.astype(str).str.contains('collaboration_quality').any(), axis=1)].index
    if len(idx) == 0:
        return None
    start = idx[0] + 1
    # Find the next 'Grand Total' after this
    for i in range(start, min(start+10, len(df_feedback))):
        if df_feedback.iloc[i].astype(str).str.contains('Grand Total').any():
            end = i
            break
    else:
        end = start + 4  # fallback
    # Extract rows
    section = df_feedback.iloc[start:end]
    # Get quality and count columns
    qualities = []
    counts = []
    for _, row in section.iterrows():
        try:
            quality = str(row[1])
            count = int(str(row[2]).replace(',',''))
            if quality.lower() not in ['nan', 'null', 'grand total']:
                qualities.append(quality)
                counts.append(count)
        except:
            continue
    if qualities and counts:
        return pd.DataFrame({'Consultation Quality': qualities, 'Count': counts})
    return None

# --- Load Data ---
with st.spinner("Loading data..."):
    # Main ticket data (granular)
    if os.path.exists(main_file):
        try:
            df_main = load_large_csv(main_file, nrows=200_000)  # adjust nrows if needed
        except Exception as e:
            st.error(f"Error loading main file: {e}")
            df_main = pd.DataFrame()
    else:
        st.warning(f"File not found: {main_file}")
        df_main = pd.DataFrame()

    # Feedback summary
    if os.path.exists(feedback_file):
        df_feedback = pd.read_csv(feedback_file, header=None, on_bad_lines='skip')
    else:
        df_feedback = pd.DataFrame()

    # Chat summary
    if os.path.exists(chat_file):
        df_chat = pd.read_csv(chat_file)
    else:
        df_chat = pd.DataFrame()

    # Overview summary
    if os.path.exists(overview_file):
        df_overview = pd.read_csv(overview_file)
    else:
        df_overview = pd.DataFrame()

# --- SSA Performance Section ---
st.header("1. SSA Performance Overview")
if not df_main.empty:
    # Resolution status breakdown
    res_counts = df_main['Resolution status'].value_counts().reset_index()
    res_counts.columns = ['Resolution status', 'Count']
    fig1 = px.pie(res_counts, names='Resolution status', values='Count', title='Resolution Status Distribution')
    st.plotly_chart(fig1, use_container_width=True)

    # Escalation rate
    esc_count = (df_main['Resolution status'].str.lower() == 'escalated').sum()
    total = len(df_main)
    st.metric("Escalation Rate", f"{esc_count/total:.1%}")
else:
    st.info("Main ticket data not loaded.")

# --- Consultation Quality Pie Chart ---
if not df_feedback.empty:
    collab_quality_df = extract_collab_quality(df_feedback)
    if collab_quality_df is not None:
        st.subheader("Consultation Quality (SSA Feedback)")
        fig_cq = px.pie(collab_quality_df, names='Consultation Quality', values='Count', title='Consultation Quality Distribution')
        st.plotly_chart(fig_cq, use_container_width=True)
    else:
        st.info("Consultation quality data not found in feedback file.")
else:
    st.info("Feedback summary not loaded.")

# --- Chat/Overview Metrics ---
st.subheader("Consulted vs Not Consulted Metrics")
if not df_chat.empty:
    st.dataframe(df_chat)
if not df_overview.empty:
    st.dataframe(df_overview)

# --- Reasons for Consultation ---
st.header("2. Reasons for SA Consultation")
if not df_main.empty:
    # Combine topic/about/description for word frequency
    text = (
        df_main['Topic of consultation'].astype(str) + ' ' +
        df_main['About tag'].astype(str) + ' ' +
        df_main['Description of merchant issue'].astype(str)
    ).str.cat(sep=' ').lower()
    words = [w for w in text.split() if len(w) > 3]
    word_freq = Counter(words)
    # Remove stopwords
    stopwords = ['shopify', 'merchant', 'like', 'that', 'them', 'want', 'using', 'when', 'would', 'they', 'from', 'wants', 'trying', 'having', 'there', 'been', 'their']
    for stopword in stopwords:
        if stopword in word_freq:
            del word_freq[stopword]
    # Get next 2 most common words
    next_top_words = [w for w, _ in word_freq.most_common(2)]
    # Generate word cloud
    from wordcloud import WordCloud
    wc = WordCloud(width=800, height=400, background_color='white', max_words=50).generate_from_frequencies(word_freq)
    img = wc.to_image()
    st.subheader("Consultation Reasons Word Cloud")
    st.image(img, use_container_width=True)
    st.markdown(f"**Next Top Words (excluding stopwords):** {', '.join(next_top_words)}")
else:
    st.info("Main ticket data not loaded.")

# --- Resources Section ---
st.header("3. Resources")
if not df_feedback.empty:
    # --- Pie chart for Resource Quality ---
    # Find the row where 'resolution_resource_quality' appears
    idx = df_feedback[df_feedback.apply(lambda row: row.astype(str).str.contains('resolution_resource_quality').any(), axis=1)].index
    if len(idx) > 0:
        start = idx[0] + 1
        # Find the next 'Grand Total' after this
        for i in range(start, min(start+10, len(df_feedback))):
            if df_feedback.iloc[i].astype(str).str.contains('Grand Total').any():
                end = i
                break
        else:
            end = start + 4  # fallback
        section = df_feedback.iloc[start:end]
        qualities = []
        counts = []
        for _, row in section.iterrows():
            try:
                quality = str(row[1])
                count = int(str(row[2]).replace(',',''))
                if quality.lower() not in ['nan', 'null', 'grand total']:
                    qualities.append(quality)
                    counts.append(count)
            except:
                continue
        if qualities and counts:
            resource_quality_df = pd.DataFrame({'Resource Quality': qualities, 'Count': counts})
            st.subheader("Resource Quality Feedback")
            fig_rq = px.pie(resource_quality_df, names='Resource Quality', values='Count', title='Resource Quality Distribution')
            st.plotly_chart(fig_rq, use_container_width=True)
        else:
            st.info("Resource quality data not found in feedback file.")
    else:
        st.info("Resource quality section not found in feedback file.")

    # --- Table of most common resource_url items (all links in file, normalized) ---
    def normalize_url(url):
        url = url.strip().lower()
        url = re.split(r'[?#]', url)[0]  # Remove query params and fragments
        return url
    all_links = []
    for col in df_feedback.columns:
        all_links += df_feedback[col].dropna().astype(str).tolist()
    # Filter for valid URLs
    all_links = [link for link in all_links if 'http' in link]
    # Normalize URLs
    all_links = [normalize_url(link) for link in all_links]
    from collections import Counter
    link_counts = Counter(all_links)
    top_links = link_counts.most_common(20)
    top_resources_df = pd.DataFrame(top_links, columns=['Resource URL', 'Count'])
    st.subheader("Top Resources Used to Resolve Issues (by Link Frequency, Normalized)")
    st.dataframe(top_resources_df)
else:
    st.info("Feedback summary not loaded.")

st.caption("SSA Dashboard | Company-level rollup | Powered by Streamlit & Plotly") 