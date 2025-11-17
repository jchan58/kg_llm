import streamlit as st
import pandas as pd
from pymongo import MongoClient
import datetime

MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["kgxllm"]
users_collection = db["users"]

assignments_df = pd.read_csv("example_login.csv")
assignments_df["user"] = assignments_df["user"].str.lower().str.strip()

st.title("KGxLLM Annotation - Login")

# session init
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:

    email = st.text_input("Enter your email").strip().lower()

    if st.button("Enter"):
        if not email:
            st.error("Please enter your email.")
            st.stop()

        if email not in assignments_df["user"].tolist():
            st.error("This email is not approved for the study.")
            st.stop()

        assigned_disease = (
            assignments_df.loc[
                assignments_df["user"] == email, "disease"
            ].iloc[0].lower().strip()
        )

        user = users_collection.find_one({"email": email})

        if not user:
            users_collection.insert_one({
                "email": email,
                "assigned_disease": assigned_disease,
                "last_drug": None,
                "created_at": datetime.datetime.utcnow(),
            })
        else:
            assigned_disease = user["assigned_disease"]  # ensure consistency

        st.session_state.logged_in = True
        st.session_state.user_email = email
        st.session_state.assigned_disease = assigned_disease
        st.session_state.last_drug = (
            user.get("last_drug") if user else None
        )

        st.success(f"Welcome! You are assigned: {assigned_disease.title()}")
        st.switch_page("pages/annotation.py")

else:
    st.switch_page("pages/annotation.py")
