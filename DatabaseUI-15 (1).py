#!/usr/bin/env python
# coding: utf-8

import streamlit as st
import pandas as pd
import numpy as np
import soundfile as sf
import io
from scipy.io import wavfile
from pymongo import MongoClient

# ---------- PASSWORD PROTECTION ---------- #
PASSWORD = "Access2025"
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
        else:
            st.error("Incorrect password.")
    st.stop()

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
            else:
                st.error("Incorrect password.")
        st.stop()

# ---------- CONFIGURE PAGE ---------- #
st.set_page_config(page_title="Lab Database", layout="wide", initial_sidebar_state="auto")

# ---------- MONGO CONNECTION ---------- #
MONGO_URI = "mongodb+srv://Guest:Guest@cluster0.6jffooa.mongodb.net/"
DB_NAME = "lab_database"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

neurogram_collection = db["neurogram_data"]
functional_collection = db["functional_data"]

# ---------- LOAD NEUROGRAM DATA ---------- #
data = list(neurogram_collection.find({}))
if not data:
    st.error("No neurogram data found in MongoDB.")
    st.stop()

df = pd.DataFrame(data)
df["Date Recorded"] = pd.to_datetime(df["Date Recorded"], errors="coerce")

hide_cols = ["_id", "Id", "Start time", "Completion time", "Email", "Name"]
gcs_cols = [col for col in df.columns if "GCS Folder" in col]
if not gcs_cols:
    st.error("No GCS Folder column found.")
    st.stop()
gcs_col = gcs_cols[0]

if "df" not in st.session_state:
    st.session_state.df = df.copy()

# ---------- HEADER ---------- #
st.markdown("<h1 style='text-align: center;'>Lab Database</h1>", unsafe_allow_html=True)

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

    if st.button("Save Changes to MongoDB"):
        neurogram_collection.delete_many({})
        neurogram_collection.insert_many(editable_df.to_dict("records"))
        st.session_state.df = editable_df.copy()
        st.success("Changes saved to MongoDB!")

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
            if col == "Date Recorded" and hasattr(val, "strftime"):
                new_row[col] = pd.to_datetime(val)
            else:
                new_row[col] = val
        neurogram_collection.insert_one(new_row)
        st.session_state.df = pd.DataFrame(list(neurogram_collection.find({})))
        st.success("New recording added to MongoDB!")

# ---------- PAGE: FUNCTIONAL DATA ---------- #
elif page == "Functional Data":
    st.markdown("<div class='section-title'>Functional Data Search</div>", unsafe_allow_html=True)

    data = list(functional_collection.find({}))
    if not data:
        st.error("No functional data found in MongoDB.")
        st.stop()

    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Filters (same as before) ...
    # [keeping your filter logic here, now powered by MongoDB]
