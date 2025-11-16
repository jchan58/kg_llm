import streamlit as st
import pandas as pd
from pymongo import MongoClient
from streamlit_extras.switch_page_button import switch_page
import datetime 

# connect to MongoDB
MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["kgxllm"]
disease_collection = db["diseases"]
users_collection = db["users"]

# login in 
assignments_df = pd.read_csv("example_login.csv")
assignments_df["user"] = assignments_df["user"].str.lower().str.strip()

# print the title
st.title("KGxLLM Annotation - Login")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in: 
    user_email = st.text_input("Enter your email").strip().lower()
    if st.button("Enter"):
        if not user_email: 
            st.error("Please enter your email.")
            st.stop()
        
        if user_email not in assignments_df['user'].tolist(): 
            st.error("This email is not approved for the study.")
            st.stop()

        # look up assigned disease
        assigned_disease = assignments_df.loc[assignments_df["user"] == user_email, "disease"].iloc[0]
        user = users_collection.find_one({"email": user_email})
        if not user:
            users_collection.insert_one({
                "email": user_email,
                "assigned_disease": assigned_disease,
                "created_at": datetime.datetime.utcnow()
            })

        # save the information 
        st.session_state.logged_in = True
        st.session_state.user_email = user_email
        st.session_state.assigned_disease = assigned_disease

        st.success(f"Welcome! You're assigned to annotate: {assigned_disease}")
        st.switch_page("pages/annotation.py")
else:
    st.switch_page("pages/annotation.py")