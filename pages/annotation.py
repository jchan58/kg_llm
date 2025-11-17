import streamlit as st
from pymongo import MongoClient
from streamlit_extras.switch_page_button import switch_page

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("Please return to the login page.")
    st.stop()

email = st.session_state.user_email
assigned_disease = st.session_state.assigned_disease.lower().strip()

MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["kgxllm"]
diseases_collection = db["diseases"]

doc = diseases_collection.find_one({"disease": assigned_disease})
if not doc:
    st.error(f"Disease '{assigned_disease}' not found in MongoDB.")
    st.stop()

drug_map = doc["drug_map"]

def find_next_drug():
    for drug, data in drug_map.items():
        q = data.get("questionnaire", {})
        if any(v in ["", None, [], {}] for v in q.values()):
            return drug
    return None

current_drug = find_next_drug()
if current_drug is None:
    st.success("🎉 All drugs are fully annotated!")
    st.stop()


st.title(f"{assigned_disease.title()} — Drug Annotation")
st.header(f"Drug: **{current_drug.title()}**")

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
Q1_mapping = {
    "Of interest": "Of_interest",
    "Not of interest": "Not_of_interest",
    "Have already tested": "Have_already_tested",
}

Q1_reverse = {v: k for k, v in Q1_mapping.items()}
stored_q1_raw = questionnaire.get(UI_TO_DB["Q1"], "")
stored_q1 = Q1_reverse.get(stored_q1_raw, "")

Q1 = st.radio(
    "Q1. Is this drug of interest for repurposing? (Please select one)",
    [""] + Q1_options,
    index=([""] + Q1_options).index(stored_q1),
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

Q2_mapping = {
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

Q2_reverse = {v: k for k, v in Q2_mapping.items()}

stored_q2_raw = questionnaire.get(UI_TO_DB["Q2"], [])
if isinstance(stored_q2_raw, str) and stored_q2_raw != "":
    stored_q2_raw = [stored_q2_raw] 

stored_q2_labels = [Q2_reverse[v] for v in stored_q2_raw if v in Q2_reverse]

Q2 = st.multiselect(
    "Q2. What is the current testing status of this drug? (Select all that apply or specify numeric code)",
    Q2_labels,
    default=stored_q2_labels,
)

Q2_internal = [Q2_mapping[l] for l in Q2]

def bool_to_index(value):
    return 0 if value is True else 1 

def radio_boolean(label, stored_bool):
    idx = bool_to_index(stored_bool)
    result = st.radio(label, ["Yes", "No"], index=idx)
    return True if result == "Yes" else False

Q3 = radio_boolean("Q3. Can this drug be consider as a combination therapy to the disease", questionnaire.get(UI_TO_DB["Q3"]))
Q4 = radio_boolean("Q4. Does GPT’s reasoning make sense for this drug?", questionnaire.get(UI_TO_DB["Q4"]))
Q6 = radio_boolean("Q6. Neurotoxicity Concern", questionnaire.get(UI_TO_DB["Q6"]))


Q5_text = st.text_input(
    "Q5. Delivery Method Notes (e.g., oral, IV, nanoparticle, etc.)",
    value=questionnaire.get(UI_TO_DB["Q5"], "")
)

Q7_pmids = st.text_area(
    "Q7. Supporting Evidence (PMID / PubMed references), seperate PMIDs by commas",
    value=", ".join(questionnaire.get(UI_TO_DB["Q7"], []))
)

Q8_notes = st.text_area(
    "Q8. Additional Notes (optional)",
    value=questionnaire.get(UI_TO_DB["Q8"], "")
)

if st.button("Next"):

    new_data = {
        UI_TO_DB["Q1"]: Q1_mapping.get(Q1, "") if Q1 else "",
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

    st.success("Saved!")
    st.rerun()
