#!/usr/bin/env python
# coding: utf-8

import streamlit as st
import pandas as pd
import numpy as np
import soundfile as sf
import io
from scipy.io import wavfile

# ---------- PASSWORD PROTECTION ---------- #

PASSWORD = "Access2025"  # Change this to your desired password
PASSWORD2 = "Krish2025"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Secure Access")
    password_input = st.text_input("Enter the password to access this page:", type="password")

    if st.button("Submit"):
        if password_input == PASSWORD:
            st.session_state.authenticated = True
            st.success("Access granted!")
            # st.experimental_rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

# ---------- ADDITIONAL PASSWORD GATE FUNCTION ---------- #
# To require an extra password check on certain pages
def password_gate():
    if "extra_authenticated" not in st.session_state:
        st.session_state.extra_authenticated = False

    if not st.session_state.extra_authenticated:
        st.title("🔒 Additional Password Required")
        password_input = st.text_input("Enter the password to access this page:", type="password")
        if st.button("Submit Extra Password"):
            if password_input == PASSWORD2:
                st.session_state.extra_authenticated = True
                st.success("Extra access granted!")
               # st.experimental_rerun()
            else:
                st.error("Incorrect password.")
        st.stop()


# ---------- CONFIGURE PAGE ---------- #
st.set_page_config(
    page_title="Lab Database",
    layout="wide",
    initial_sidebar_state="auto"
)

# ---------- CUSTOM CSS ---------- #
st.markdown("""
    <style>
        body {
            background-color: #f5f9ff;
        }
        .stApp {
            font-family: "Segoe UI", sans-serif;
        }
        h1 {
            color: #154c79;
            margin-top: 10px;
            margin-bottom: 20px;
        }
        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #154c79;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }
        .result-card {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0px 0px 8px rgba(0, 0, 0, 0.05);
        }
        .button-link {
            background-color: #0072b5;
            color: white !important;
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            display: inline-block;
            margin-top: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# ---------- LOAD DATA ---------- #
csv_file = "Neurogram Experimental Data 1(Sheet1) (3).csv"
try:
    df = pd.read_csv(csv_file)
except FileNotFoundError:
    st.error("CSV file not found. Please upload or place the file in the working directory.")
    st.stop()

df["Date Recorded"] = pd.to_datetime(df["Date Recorded"], errors="coerce")
hide_cols = ["Id", "Start time", "Completion time", "Email", "Name"]
gcs_cols = [col for col in df.columns if "GCS Folder" in col]
if not gcs_cols:
    st.error("No GCS Folder column found.")
    st.stop()
gcs_col = gcs_cols[0]

if "df" not in st.session_state:
    st.session_state.df = df.copy()

# ---------- HEADER ---------- #
st.markdown("""
    <h1 style='text-align: center;'>Lab Database</h1>
""", unsafe_allow_html=True)

# ---------- PAGE NAVIGATION ---------- #
page = st.selectbox("Choose a Section", [
    "Neurogram Finder",
    "Central Database",
    "Add New Recording",
    "Functional Data",
    "Scramble Audio",
    "Change Carrier Frequency" 
])

# ---------- PAGE: FINDER ---------- #
if page == "Neurogram Finder":
    st.markdown("<div class='section-title'>Search Criteria</div>", unsafe_allow_html=True)
    df = st.session_state.df

    mediator = st.selectbox("1. Select Mediator", sorted(df["Mediator"].dropna().unique()))
    filtered = df[df["Mediator"] == mediator]

    responder = st.radio("2. Responder Status", ["All", "Yes", "No"], horizontal=True)
    if responder != "All":
        filtered = filtered[filtered["Responder"].str.lower() == responder.lower()]

    methods = sorted(filtered["Administration Method"].dropna().unique())
    admin_method = st.selectbox("3. Administration Method", ["All"] + methods)
    if admin_method != "All":
        filtered = filtered[filtered["Administration Method"] == admin_method]

    gcs_option = st.radio("4. GCS Folder Link", ["All", "Yes", "No"], horizontal=True)
    has_link = filtered[gcs_col].notna()
    if gcs_option == "Yes":
        filtered = filtered[has_link]
    elif gcs_option == "No":
        filtered = filtered[~has_link]

    if not filtered["Date Recorded"].dropna().empty:
        start_date, end_date = st.date_input(
            "5. Date Range",
            [filtered["Date Recorded"].min(), filtered["Date Recorded"].max()]
        )
        filtered = filtered[
            (filtered["Date Recorded"] >= pd.to_datetime(start_date)) &
            (filtered["Date Recorded"] <= pd.to_datetime(end_date))
        ]

    st.markdown("---")
    st.markdown("### Matching Results")

    if filtered.empty:
        st.warning("No recordings found. Try adjusting the filters.")
    else:
        st.markdown(f"**Total Results:** {len(filtered)}")

        for idx, row in filtered.iterrows():
            title = str(row.get("Recording File Name", f"Recording {idx+1}"))
            with st.expander(title):
                for col in filtered.columns:
                    if col in hide_cols:
                        continue
                    val = row[col]
                    if pd.notna(val):
                        if col == gcs_col:
                            st.markdown(
                                f"<a href='{val}' target='_blank' class='button-link'>Open Folder</a>",
                                unsafe_allow_html=True
                            )
                        elif isinstance(val, pd.Timestamp):
                            st.markdown(f"**{col.strip()}:** {val.strftime('%B %d, %Y')}")
                        else:
                            st.markdown(f"**{col.strip()}:** {val}")

# ---------- PAGE: DATABASE ---------- #
elif page == "Central Database":
    st.header("Central Database")
    df = st.session_state.df

    editable_df = st.data_editor(
        df.drop(columns=hide_cols, errors="ignore"),
        use_container_width=True,
        num_rows="dynamic",
        key="editable_table"
    )

    st.download_button(
        "Download Edited CSV",
        data=editable_df.to_csv(index=False),
        file_name="edited_neurogram_data.csv",
        mime="text/csv"
    )

    if st.button("Save Changes to File"):
        st.session_state.df = editable_df.copy()
        st.session_state.df.to_csv(csv_file, index=False)
        st.success("Changes saved to Neurogram_Chat_With_GCS_Folder.csv")

# ---------- PAGE: ADD RECORD ---------- #
elif page == "Add New Recording":
    st.header("Add New Recording")
    df = st.session_state.df
    inputs = {}

    for col in df.columns:
        if col in hide_cols:
            continue
        col_dtype = df[col].dtype
        key_input = f"input_{col}"

        if pd.api.types.is_datetime64_any_dtype(col_dtype):
            inputs[col] = st.date_input(f"{col}", key=key_input)
        elif pd.api.types.is_numeric_dtype(col_dtype):
            inputs[col] = st.number_input(f"{col}", value=0.0, format="%.5f", key=key_input)
        else:
            inputs[col] = st.text_input(f"{col}", value="", key=key_input)

    if st.button("Add Recording"):
        new_row = {}
        for col, val in inputs.items():
            if col == "Date Recorded" and isinstance(val, pd._libs.tslibs.timestamps.Timestamp):
                new_row[col] = pd.to_datetime(val)
            else:
                new_row[col] = val
        new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        st.session_state.df = new_df
        st.session_state.df.to_csv(csv_file, index=False)
        st.success("New recording added and saved!")

# ---------- PAGE: FUNCTIONAL DATA ---------- #
elif page == "Functional Data":
    st.markdown("<div class='section-title'>Functional Data Search</div>", unsafe_allow_html=True)

    # Excel file (update path if needed)
    excel_file_path = "Functional Data_Master List (1).xlsx"
    try:
        df = pd.read_excel(excel_file_path, sheet_name="Functional data")
    except FileNotFoundError:
        st.error("Excel file not found. Please upload or place the file in the working directory.")
        st.stop()

    # Clean up
    df.columns = df.columns.str.strip()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Dropdown filters
    mediator_options = sorted(df["Mediator"].dropna().unique()) if "Mediator" in df.columns else []
    type_options = sorted(df["Type"].dropna().unique()) if "Type" in df.columns else []
    ip_options = sorted(df["i.p./Neurogram"].dropna().unique()) if "i.p./Neurogram" in df.columns else []
    researcher_options = sorted(df["Researcher"].dropna().unique()) if "Researcher" in df.columns else []
    category_options = sorted(df["Category"].dropna().unique()) if "Category" in df.columns else []
    success_options = sorted(df["Success (Yes/No)"].dropna().unique()) if "Success (Yes/No)" in df.columns else []

    selected_mediator = st.selectbox("Mediator", ["All"] + mediator_options)
    selected_type = st.selectbox("Clinical / Preclinical", ["All"] + type_options)
    selected_ip = st.selectbox("Neurogram or i.p.", ["All"] + ip_options)
    selected_researcher = st.selectbox("Researcher", ["All"] + researcher_options)
    selected_category = st.selectbox("Category", ["All"] + category_options)
    selected_success = st.selectbox("Success (Yes/No)", ["All"] + success_options)

    # Date filter
    if "Date" in df.columns and not df["Date"].dropna().empty:
        date_min, date_max = df["Date"].min(), df["Date"].max()
        start_date, end_date = st.date_input("Date Range", [date_min, date_max])
    else:
        start_date, end_date = None, None

    # Apply filters
    filtered = df.copy()
    if selected_mediator != "All":
        filtered = filtered[filtered["Mediator"] == selected_mediator]
    if selected_type != "All":
        filtered = filtered[filtered["Type"] == selected_type]
    if selected_category != "All":
        filtered = filtered[filtered["Category"] == selected_category]
    if selected_ip != "All":
        filtered = filtered[filtered["i.p./Neurogram"] == selected_ip]
    if selected_researcher != "All":
        filtered = filtered[filtered["Researcher"] == selected_researcher]
    if selected_success != "All":
        filtered = filtered[filtered["Success (Yes/No)"] == selected_success]
    if start_date and end_date:
        filtered = filtered[
            (filtered["Date"] >= pd.to_datetime(start_date)) &
            (filtered["Date"] <= pd.to_datetime(end_date))
        ]

    # Display results
    st.markdown("---")
    st.markdown("### Matching Results")

    if filtered.empty:
        st.warning("No functional data found. Try adjusting the filters.")
    else:
        st.markdown(f"**Total Results:** {len(filtered)}")
        for idx, row in filtered.iterrows():
            title = row.get("Experiment", f"Record {idx+1}")
            with st.expander(str(title)):
                for col in filtered.columns:
                    val = row[col]
                    if pd.notna(val):
                        if col == "GCS LINK":
                            st.markdown(
                                f"<a href='{val}' target='_blank' class='button-link'>Open GCS Link</a>",
                                unsafe_allow_html=True
                            )
                        elif isinstance(val, pd.Timestamp):
                            st.markdown(f"**{col.strip()}:** {val.strftime('%B %d, %Y')}")
                        else:
                            st.markdown(f"**{col.strip()}:** {val}")

# ---------- PAGE: SCRAMBLE AUDIO ---------- #
elif page == "Scramble Audio":
    password_gate()  # Extra password check here

    st.markdown("<div class='section-title'>Scramble Uploaded Audio</div>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload a .wav file to scramble", type=["wav"])

    segment_duration = st.number_input(
        "Scramble Segment Duration (in seconds)", 
        min_value=0.001, 
        max_value=1.0, 
        value=0.05, 
        step=0.001, 
        format="%.3f"
    )

    if uploaded_file is not None:
        def scramble_audio_bytes(input_file, segment_duration):
            import tempfile

            # Save uploaded file to a temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(input_file.read())
                tmp_path = tmp.name

            sr, audio = wavfile.read(tmp_path)
            audio = audio.astype(np.float32) / np.max(np.abs(audio))  # normalize

            segment_samples = int(segment_duration * sr)
            segments = [audio[i:i + segment_samples] for i in range(0, len(audio), segment_samples)]
            np.random.shuffle(segments)
            scrambled_audio = np.concatenate(segments)

            buffer = io.BytesIO()
            sf.write(buffer, scrambled_audio, sr, format='WAV')
            buffer.seek(0)
            return buffer

        if st.button("Scramble Audio"):
            scrambled_wav = scramble_audio_bytes(uploaded_file, segment_duration)
            st.success(f"Audio scrambled using {segment_duration:.3f} sec segments!")
            st.audio(scrambled_wav, format='audio/wav')
            st.download_button(
                label="Download Scrambled Audio",
                data=scrambled_wav,
                file_name="scrambled_audio.wav",
                mime="audio/wav"
            )

# ---------- PAGE: CHANGE CARRIER FREQUENCY ---------- #
elif page == "Change Carrier Frequency":
    password_gate()  # Extra password check here

    st.markdown("<div class='section-title'>Carrier Frequency Modulation</div>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload a .wav file to modulate", type=["wav"])

    carrier_freq = st.number_input(
        "Carrier Frequency (Hz)",
        min_value=100.0,
        max_value=50000.0,
        value=15000.0,
        step=100.0,
        format="%.1f"
    )

    if uploaded_file is not None:
        def apply_am_carrier(input_file, carrier_freq):
            import tempfile
            from scipy.io import wavfile

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(input_file.read())
                tmp_path = tmp.name

            sr, audio = wavfile.read(tmp_path)

            # Handle stereo by converting to mono
            if audio.ndim > 1:
                audio = audio.mean(axis=1)

            # Normalize
            audio = audio.astype(np.float32)
            audio /= np.max(np.abs(audio))

            t = np.arange(len(audio)) / sr
            carrier = np.cos(2 * np.pi * carrier_freq * t)

            # Apply amplitude modulation
            modulated = audio * carrier

            # Re-normalize
            modulated /= np.max(np.abs(modulated))

            buffer = io.BytesIO()
            sf.write(buffer, modulated, sr, format='WAV')
            buffer.seek(0)
            return buffer

        if st.button("Modulate Audio"):
            modulated_wav = apply_am_carrier(uploaded_file, carrier_freq)
            st.success(f"Audio modulated with {carrier_freq:.1f} Hz carrier!")
            st.audio(modulated_wav, format='audio/wav')
            st.download_button(
                label="Download Modulated Audio",
                data=modulated_wav,
                file_name=f"modulated_{int(carrier_freq)}Hz.wav",
                mime="audio/wav"
            )
