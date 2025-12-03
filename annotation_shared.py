import streamlit as st
from pymongo import MongoClient
import re

# remove the space
st.html("""
<style>
/* Radio */
div[data-testid="stRadio"] > div {
    margin-top: -30px !important;
}

/* Text area */
div[data-testid="stTextArea"] > div {
    margin-top: -30px !important;
}

/* Multiselect */
div[data-testid="stMultiSelect"] > div {
    margin-top: -30px !important;
}
</style>
""")

def display_disease_name(d):
    d = d.lower()
    if d.endswith("cancer") and " " not in d:
        return d.replace("cancer", " cancer").title()
    return d.title()

def bracket_url_to_md(text):
    if text is None:
        return ""
    text = str(text)
    pattern = r"\[(https?://[^\]]+)\]"
    repl = r"<\1>"
    return re.sub(pattern, repl, text)

def format_reference(ref):
    if isinstance(ref, str):
        return bracket_url_to_md(ref)
    elif isinstance(ref, dict):
        title = ref.get("study_summary", {}).get("title", "")
        nct = ref.get("nct_id", "")
        url = f"https://clinicaltrials.gov/study/{nct}" if nct else ""
        if url:
            return f"**{title}** — [{nct}]({url})"
        else:
            return f"**{title}**"
    return ""

def run_annotation(assigned_disease):
    # hide Streamlit sidebar
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] { display: none; }
            [data-testid="stSidebar"] { background-color: white; }
        </style>
    """, unsafe_allow_html=True)

    # confirmation of moving on to next drug 
    if "confirm_next" not in st.session_state: 
        st.session_state.confirm_next = False
    # auto email (no login)
    email = f"auto_user_{assigned_disease}"
    st.session_state.user_email = email
    st.session_state.assigned_disease = assigned_disease.lower().strip()

    if "navigate_to" not in st.session_state:
        st.session_state.navigate_to = None

    # DB setup
    client = MongoClient(st.secrets["MONGO_URI"])
    db = client["kgxllm"]
    diseases_collection = db["diseases"]
    users_collection = db["users"]

    doc = diseases_collection.find_one({"disease": assigned_disease})
    if not doc:
        st.error(f"Disease '{assigned_disease}' not found.")
        st.stop()

    drug_map = doc["drug_map"]
    updates_needed = {}
    for drug, data in drug_map.items():
        if "completed" not in data:
            updates_needed[f"drug_map.{drug}.completed"] = False

    if updates_needed:
        diseases_collection.update_one(
            {"disease": assigned_disease},
            {"$set": updates_needed}
        )
        doc = diseases_collection.find_one({"disease": assigned_disease})
        drug_map = doc["drug_map"]

    def is_completed(drug):
           return drug_map[drug].get("completed", False)

    # pick next drug
    def get_next_drug():
        for drug in drug_map.keys():
            if not is_completed(drug):
                return drug
        return None

    # navigation
    current_drug = st.session_state.navigate_to or get_next_drug()

    if current_drug is None:
        st.success("🎉 All drugs annotated!")
        st.stop()

    drug_list = list(drug_map.keys())
    st.sidebar.title("Drugs")

    for drug in drug_list:
        done = is_completed(drug)

        # highlight active drug
        if drug == current_drug:
            st.sidebar.markdown(
                f"""
                <div style="
                    padding:8px;
                    background:#e7f0ff;
                    border-radius:6px;
                    margin-bottom:4px;
                ">
                👉 <strong>{drug}</strong> {'✔️' if done else ''}
                </div>
                """,
                unsafe_allow_html=True
            )

        else:
            label = f"{drug} {'✔️' if done else ''}"
            if st.sidebar.button(label, key=f"nav_{drug}", use_container_width=True):
                st.session_state.navigate_to = drug
                st.session_state.last_drug = drug
                st.rerun()
    disease_title = display_disease_name(assigned_disease)
    st.title(f"{disease_title} — Drug Annotation")
    drug_list = list(drug_map.keys())
    total_drugs = len(drug_list)
    completed_count = sum(1 for drug in drug_list if is_completed(drug))
    st.markdown(f"### Progress: {completed_count}/{total_drugs} completed")
    st.progress(completed_count / total_drugs)
    st.header(f"Drug: **{current_drug}**")
    questionnaire = drug_map[current_drug]
    prev_Q1 = (
    questionnaire["Q1"]["selection"]
    if "Q1" in questionnaire and isinstance(questionnaire["Q1"], dict)
        else None
    )

    Q1_options = [
        "FDA-Approved to liver cancer",
        "Completed phase III with positive result",
        "In phase III",
        "Completed phase II with positive result",
        "In phase II",
        "Completed phase I with positive result (or FDA-Approved for other diseases)",
        "In phase I",
        "Failed in any phases",
        "No — No clinical trials identified for this drug in this disease",
    ]

    if prev_Q1 == "No":
        prev_Q1 = "No — No clinical trials identified for this drug in this disease"

    st.html("""
    <div style='font-weight:600; font-size:1.4rem;'>
        Q1. What is the latest status of this drug for this disease? (single choice)
    </div>
    """)
    st.html("""
        <div style='margin-top:-8px; font-size:0.9rem; color:#666;'>
            <em>(If, and only if, you select “No,” please proceed to Q2. 
            For all other selections, please go directly to Q4.)</em>
        </div>
    """)
    Q1_value = st.radio(
        "",
        Q1_options,
        index=Q1_options.index(prev_Q1) if prev_Q1 in Q1_options else None
    )
    clinical_refs = []
    if "Q1" in questionnaire and isinstance(questionnaire["Q1"], dict):
        clinical_refs = questionnaire["Q1"].get("clinicaltrial_references", [])

    if clinical_refs:
        refs_md = "\n".join(f"- {format_reference(ref)}" for ref in clinical_refs)
    else:
        refs_md = "No clinical trial references found."

    with st.expander("Clinical Trials", expanded=True):
        st.markdown(refs_md)

    prev_Q2 = (
    [questionnaire["Q2"]["selection"]] 
    if "Q2" in questionnaire and isinstance(questionnaire["Q2"], dict)
    else questionnaire.get("Q2_preclinical_results", [])
    )

    Q2_options = [
        "Positive result in animal study",
        "Negative result in animal study",
        "Positive result in vivo result",
        "Negative result in vivo result",
        "Positive result in vitro result",
        "Negative result in vitro result",
        "Rarely discussed",
        "Irrelevant drugs",
    ]

    st.html("""
    <div style='font-weight:600; font-size:1.4rem;'>
        Q2. What is the pre-clinical result for testing this drug in this disease? (multi-choice)
    </div>
    """)
    st.html("""
        <div style='margin-top:-8px; font-size:0.9rem; color:#666;'>
            <em>(If “Rarely discussed” is selected, proceed to Q3. For all other selections, skip and go directly to Q4)</em>
        </div>
    """)
    Q2_value = st.multiselect(
        "",
        Q2_options,
        default=[v for v in prev_Q2 if v in Q2_options]
    )

    literature_refs = []
    if "Q2" in questionnaire and isinstance(questionnaire["Q2"], dict):
        literature_refs = questionnaire["Q2"].get("literature_references", [])

    if literature_refs:
        refs_md = "\n".join(f"- {bracket_url_to_md(ref)}" for ref in literature_refs)
    else:
        refs_md = "No literature references found."

    with st.expander("Literature References", expanded=True):
        st.markdown(refs_md)

    prev_Q3 = questionnaire.get("Q3_interest")
    st.html("""
    <div style='font-weight:600; font-size:1.4rem;'>
        Q3. If pre-clinical data are 'Rarely discussed,' is this drug of interest?
    </div>
    """)
    Q3_value = st.radio(
        "",
        ["Of interest", "Not of interest"],
        index=["Of interest", "Not of interest"].index(prev_Q3)
            if prev_Q3 in ["Of interest", "Not of interest"]
            else None,
    )

    prev_Q4 = questionnaire.get("Q4_notes", "")
    st.html("""
    <div style='font-weight:600; font-size:1.4rem;'>
        Q4. Additional Notes
    </div>
    """)
    Q4_value = st.text_area(
        "",
        value=prev_Q4,
        height=200
    )

    @st.dialog(" ", width="small", dismissible=False)
    def confirm_dialog():
        st.markdown("""
        <style>
        .stButton > button {
            width: 130px !important;
            padding: 0.55rem 1rem !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            font-size: 0.95rem !important;
        }

        div[data-testid="stDialog"] div[id="no_btn"] > button {
            background-color: #ffb3c6 !important;
            color: black !important;
            border: none !important;
        }
        div[data-testid="stDialog"] div[id="no_btn"] > button:hover {
            background-color: #ff8eab !important;
        }

        div[data-testid="stDialog"] div[id="yes_btn"] > button {
            background-color: #b6eeb3 !important;
            color: black !important;
            border: none !important;
        }
        div[data-testid="stDialog"] div[id="yes_btn"] > button:hover {
            background-color: #9fe79b !important;
        }
        </style>
    """, unsafe_allow_html=True)
        st.markdown(
            "<div style='text-align:center;'>Are you sure you want to move onto the next drug?</div>",
            unsafe_allow_html=True
        )
        col_sp1, col_no, col_yes, col_sp2 = st.columns([1, 1, 1, 1])

        with col_no:
            no_clicked = st.button("No", key="no_btn")

        with col_yes:
            yes_clicked = st.button("Yes", key="yes_btn")

        if no_clicked:
            st.session_state.confirm_next = False
            st.rerun()

        if yes_clicked:
            st.session_state.confirm_next = False

            new_data = {
                "Q1_latest_status": Q1_value,
                "Q2_preclinical_results": Q2_value,
                "Q3_interest": Q3_value,
                "Q4_notes": Q4_value,
            }

            updates = {
                f"drug_map.{current_drug}.{key}": val
                for key, val in new_data.items()
                if val != questionnaire.get(key, None)
            }

            if updates:
                diseases_collection.update_one(
                    {"disease": assigned_disease},
                    {"$set": updates}
                )

            diseases_collection.update_one(
                {"disease": assigned_disease},
                {"$set": {f"drug_map.{current_drug}.completed": True}}
            )

            users_collection.update_one(
                {"email": email},
                {"$set": {"last_drug": current_drug}}
            )

            st.session_state.navigate_to = None
            st.session_state.last_drug = current_drug
            st.rerun()


    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 6, 1])

    with col1:
        drug_list = list(drug_map.keys())
        idx = drug_list.index(current_drug)
        back_disabled = idx == 0
        if st.button("← Back", use_container_width=True, disabled=back_disabled):
            prev_drug = drug_list[idx - 1]
            st.session_state.navigate_to = prev_drug
            st.session_state.last_drug = prev_drug
            st.rerun()

    with col2:
        st.write("") 

    with col3:
        if st.button("Next →", use_container_width=True):
            st.session_state.confirm_next = True
            st.rerun()

    if st.session_state.confirm_next:
        confirm_dialog()
            