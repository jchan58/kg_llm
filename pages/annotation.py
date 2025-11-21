import streamlit as st
from pymongo import MongoClient


if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("Please return to the login page.")
    st.stop()

email = st.session_state.user_email
assigned_disease = st.session_state.assigned_disease.lower().strip()


MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["kgxllm"]
diseases_collection = db["diseases"]
users_collection = db["users"]

doc = diseases_collection.find_one({"disease": assigned_disease})
if not doc:
    st.error(f"Disease '{assigned_disease}' not found in database.")
    st.stop()

drug_map = doc["drug_map"]

def get_next_drug():
    drug_names = list(drug_map.keys())
    last = st.session_state.get("last_drug", None)
    if last is None:
        return drug_names[0]

    if last in drug_names:
        last_idx = drug_names.index(last)
        for drug in drug_names[last_idx+1:]:
            q = drug_map[drug].get("questionnaire", {})
            if any(v in ["", None, [], {}] for v in q.values()):
                return drug

    for drug, data in drug_map.items():
        q = data.get("questionnaire", {})
        if any(v in ["", None, [], {}] for v in q.values()):
            return drug
    return None

current_drug = get_next_drug()

if current_drug is None:
    st.success("🎉 All drugs are fully annotated!")
    st.stop()

st.title(f"{assigned_disease.title()} — Drug Annotation")

drug_list = list(drug_map.keys())
total_drugs = len(drug_list)
current_index = drug_list.index(current_drug) + 1

st.markdown(f"### Progress: {current_index} / {total_drugs} drugs annotated")
st.progress(current_index / total_drugs)
st.header(f"Drug: **{current_drug.title()}**")

if st.button("Logout"):
    users_collection.update_one(
        {"email": email},
        {"$set": {"last_drug": current_drug}}
    )
    st.session_state.clear()
    st.switch_page("app.py")

with st.expander("GPT Rationale", expanded=True):
    rationale = drug_map[current_drug].get("rationale_bullets", [])
    for bullet in rationale:
        st.markdown(f"- {bullet}")

questionnaire = drug_map[current_drug]["questionnaire"]

UI_TO_DB = {
    "Q1": "Q3_interest",
    "Q2": "Q2_Research_status",
    "Q3": "Q4_combination_therapy",
    "Q4": "Q5_reasoning_makes_sense",
    "Q5": "Q6_delivery_method_notes",
    "Q6": "Q7_neurotoxicity_concern",
    "Q7": "Q8_supporting_evidence_pmids",
    "Q8": "Q9_note",
}

Q1_options = ["Of interest", "Not of interest", "Have already tested"]
Q1_map = {
    "Of interest": "Of_interest",
    "Not of interest": "Not_of_interest",
    "Have already tested": "Have_already_tested",
}

Q1_rev = {v: k for k, v in Q1_map.items()}

stored_raw = questionnaire.get(UI_TO_DB["Q1"], "")
stored_label = Q1_rev.get(stored_raw, None)

if stored_label in Q1_options:
    default_index = Q1_options.index(stored_label)
else:
    default_index = 0 

Q1 = st.radio(
    "Q1. Is this drug of interest for repurposing? (Please select one)",
    Q1_options,
    index=default_index,
)

Q2_labels = [
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

Q2_map = {
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

Q2_rev = {v: k for k, v in Q2_map.items()}

stored_q2 = questionnaire.get(UI_TO_DB["Q2"], [])
if isinstance(stored_q2, str):
    stored_q2 = [stored_q2]

stored_labels_q2 = [Q2_rev[v] for v in stored_q2 if v in Q2_rev]

fda_val = questionnaire.get("Q1_FDA_status", "")
if fda_val in ["FDA_approved_for_[Disease]", "FDA_approved_for_other_disease"]:
    if "FDA-Approved" not in stored_labels_q2:
        stored_labels_q2.insert(0, "FDA-Approved")

Q2 = st.multiselect(
    "Q2. What is the current testing status? (Select all that apply)",
    Q2_labels,
    default=stored_labels_q2,
)

Q2_internal = [Q2_map[x] for x in Q2]

def bool_radio(label, stored):
    if stored is True:
        default = "Yes"
    elif stored is False:
        default = "No"
    else:
        default = None

    picked = st.radio(
        label,
        ["Yes", "No"],
        index=0 if default == "Yes" else 1 if default == "No" else 0
    )
    return picked == "Yes"

Q3 = bool_radio("Q3. Combination therapy possible?", questionnaire.get(UI_TO_DB["Q3"]))
Q4 = bool_radio("Q4. Does GPT's reasoning make sense?", questionnaire.get(UI_TO_DB["Q4"]))
Q6 = bool_radio("Q6. Neurotoxicity Concern?", questionnaire.get(UI_TO_DB["Q6"]))

Q5_text = st.text_input("Q5. Delivery Method Notes (e.g., oral, IV, nanoparticle, etc.)", value=questionnaire.get(UI_TO_DB["Q5"], ""))
Q7_pmids = st.text_area(
    "Q7. Supporting Evidence (PMIDs, comma-separated)",
    value=", ".join(questionnaire.get(UI_TO_DB["Q7"], [])),
)

Q8_notes = st.text_area("Q8. Additional Notes (Optional)", value=questionnaire.get(UI_TO_DB["Q8"], ""))

col1, col2 = st.columns(2)
with col1:
    drug_list = list(drug_map.keys())
    idx = drug_list.index(current_drug)

    back_disabled = idx == 0  # can't go back from the first drug

    if st.button("← Back", disabled=back_disabled):
        prev_drug = drug_list[idx - 1]
        st.session_state.last_drug = prev_drug

        users_collection.update_one(
            {"email": email},
            {"$set": {"last_drug": prev_drug}}
        )

        st.rerun()

with col2:
    if st.button("Next →"):
        new_data = {
            UI_TO_DB["Q1"]: Q1_map.get(Q1, "") if Q1 else "",
            UI_TO_DB["Q2"]: Q2_internal,
            UI_TO_DB["Q3"]: Q3,
            UI_TO_DB["Q4"]: Q4,
            UI_TO_DB["Q5"]: Q5_text,
            UI_TO_DB["Q6"]: Q6,
            UI_TO_DB["Q7"]: [p.strip() for p in Q7_pmids.split(",") if p.strip()],
            UI_TO_DB["Q8"]: Q8_notes,
        }

        updates = {}
        for key, new_val in new_data.items():
            old_val = questionnaire.get(key, "")
            if new_val != old_val:
                updates[f"drug_map.{current_drug}.questionnaire.{key}"] = new_val

        if updates:
            diseases_collection.update_one(
                {"disease": assigned_disease},
                {"$set": updates}
            )

        users_collection.update_one(
            {"email": email},
            {"$set": {"last_drug": current_drug}}
        )
        st.session_state.last_drug = current_drug

        st.success("Saved!")
        st.rerun()