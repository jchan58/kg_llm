import streamlit as st
from pymongo import MongoClient


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

    st.title(f"{assigned_disease.title()} — Drug Annotation")
    drug_list = list(drug_map.keys())
    total_drugs = len(drug_list)
    current_index = drug_list.index(current_drug) + 1
    st.markdown(f"### Progress: {current_index}/{total_drugs}")
    st.progress(current_index / total_drugs)
    st.header(f"Drug: **{current_drug}**")

    # rationale
    with st.expander("GPT Rationale", expanded=True):
        for bullet in drug_map[current_drug].get("rationale_bullets", []):
            st.markdown(f"- {bullet}")

    questionnaire = drug_map[current_drug]["questionnaire"]
    UI_TO_DB = {
        "Q1": "Q3_interest",
        "Q2_FDA": "Q1_FDA_status",
        "Q3_status": "Q2_Research_status",
        "Q4_refs": "Q8_supporting_evidence_references",
        "Q5_combo": "Q4_combination_therapy",
        "Q6_reason": "Q5_reasoning_makes_sense",
        "Q7_neuro": "Q7_neurotoxicity_concern",
        "Q8_note": "Q9_note",
    }

    Q1_options = ["Of interest", "Not of interest", "Have already tested (or FDA-approved)"]
    Q1_rev = {
        "Of_interest": "Of interest",
        "Not_of_interest": "Not of interest",
        "Have_already_tested (or FDA-approved)": "Have already tested (or FDA-approved)" 
    }

    prev_q1_raw = questionnaire.get(UI_TO_DB["Q1"], None)
    prev_q1_label = Q1_rev.get(prev_q1_raw, None)

    Q1_value = st.radio(
        "Q1. Is this drug of interest for repurposing?",
        Q1_options,
        index=Q1_options.index(prev_q1_label) if prev_q1_label in Q1_options else None,
    )

    FDA_options = [
        "FDA-Approved",
        "FDA-Approved for other diseases",
        "No",
    ]

    FDA_map = {
        "FDA-Approved": f"FDA_approved_for_{assigned_disease.lower()}",
        "FDA-Approved for other diseases": "FDA_approved_for_other_disease",
        "No": "Not_FDA_approved",
    }

    FDA_rev = {v: k for k, v in FDA_map.items()}
    prev_fda_raw = questionnaire.get(UI_TO_DB["Q2_FDA"], None)
    prev_fda_label = FDA_rev.get(prev_fda_raw, None)

    Q2_FDA_value = st.radio(
        "Q2. What is the current FDA status?",
        FDA_options,
        index=FDA_options.index(prev_fda_label) if prev_fda_label in FDA_options else 0,
    )

    STATUS_labels = [
        "FDA-Approved",
        "Positive clinical outcomes",
        "Negative clinical outcomes",
        "Positive in-vivo outcomes",
        "Negative in-vivo outcomes",
        "Positive in-vitro outcomes",
        "Negative in-vitro outcomes",
        "Rarely discussed",
        "Irrelevant drugs",
    ]

    STATUS_map = {
        "FDA-Approved": "FDA_approved_for_other_disease",
        "Positive clinical outcomes": "positive_clinical_outcomes",
        "Negative clinical outcomes": "negative_clinical_outcomes",
        "Positive in-vivo outcomes": "positive_in_vivo_outcomes",
        "Negative in-vivo outcomes": "negative_in_vivo_outcomes",
        "Positive in-vitro outcomes": "positive_in_vitro_outcomes",
        "Negative in-vitro outcomes": "negative_in_vitro_outcomes",
        "Rarely discussed": "rarely_discussed",
        "Irrelevant drugs": "irrelevant_drugs",
    }

    # prefill
    prev_q3_raw = questionnaire.get(UI_TO_DB["Q3_status"], None)
    if isinstance(prev_q3_raw, str) and prev_q3_raw.startswith("FDA_approved"):
        prev_q3_raw = "FDA_approved_for_other_disease"
    STATUS_rev = {v: k for k, v in STATUS_map.items()}
    prev_q3_label = STATUS_rev.get(prev_q3_raw, None)

    Q3_label = st.radio(
        "Q3. What is the current testing status?",
        STATUS_labels,
        index=STATUS_labels.index(prev_q3_label) if prev_q3_label in STATUS_labels else None,
    )

    Q3_internal = STATUS_map[Q3_label]


    ### ---------- Q4 (required text input, prefilled) ----------
    prev_refs = questionnaire.get(UI_TO_DB["Q4_refs"], [])
    Q4_refs_input = st.text_area(
        "Q4. Supporting Evidence (references)",
        value="\n".join(prev_refs) if prev_refs else "", 
        height=300
    )
    Q4_refs = [r.strip() for r in Q4_refs_input.split("\n") if r.strip()]

    def yes_no_radio(label, stored):
        hint = f" _(previous: {'Yes' if stored else 'No'})_" if stored in [True, False] else ""
        choices = ["N/A", "Yes", "No"]
        val = st.radio(label + hint, choices, index=0)
        if val == "N/A":
            return None 
        return val

    Q5_combo = yes_no_radio("Q5. Combination therapy possible?", questionnaire.get(UI_TO_DB["Q5_combo"]))
    Q6_reason = yes_no_radio("Q6. Does GPT's reasoning make sense?", questionnaire.get(UI_TO_DB["Q6_reason"]))
    Q7_neuro = yes_no_radio("Q7. Neurotoxicity Concern?", questionnaire.get(UI_TO_DB["Q7_neuro"]))
    Q8_note = st.text_area(
        "Q8. Additional Notes (Optional)",
        value=questionnaire.get(UI_TO_DB["Q8_note"], "")
    )

    @st.dialog("", width="small", dismissible=False)
    def confirm_dialog():
        st.markdown("""
            <style>
            /* Make buttons larger */
            .stButton > button {
                width: 130px !important;
                padding: 0.55rem 1rem !important;
                font-weight: 600 !important;
                border-radius: 8px !important;
                font-size: 0.95rem !important;
            }

            /* Pink NO button */
            div[data-testid="stDialog"] div[id="no_btn"] > button {
                background-color: #ffb3c6 !important;
                color: black !important;
                border: none !important;
            }
            div[data-testid="stDialog"] div[id="no_btn"] > button:hover {
                background-color: #ff8eab !important;
            }

            /* Green YES button */
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

        # centered prompt
        st.markdown(
            "<div style='text-align:center;'>Are you sure you want to move onto the next drug?</div>",
            unsafe_allow_html=True
        )

        # 4 columns for true centering
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
                UI_TO_DB["Q1"]: Q1_value,
                UI_TO_DB["Q2_FDA"]: FDA_map.get(Q2_FDA_value, ""),
                UI_TO_DB["Q3_status"]: Q3_internal,
                UI_TO_DB["Q4_refs"]: Q4_refs,
                UI_TO_DB["Q5_combo"]: (Q5_combo == "Yes") if Q5_combo else None,
                UI_TO_DB["Q6_reason"]: (Q6_reason == "Yes") if Q6_reason else None,
                UI_TO_DB["Q7_neuro"]: (Q7_neuro == "Yes") if Q7_neuro else None,
                UI_TO_DB["Q8_note"]: Q8_note,
            }

            updates = {
                f"drug_map.{current_drug}.questionnaire.{key}": val
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
            