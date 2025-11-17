import streamlit as st
from pymongo import MongoClient
from streamlit_extras.switch_page_button import switch_page

# check if the user is logged in 
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("Please return to the login page.")
    st.stop()

email = st.session_state.user_email
assigned_disease = st.session_state.assigned_disease

# mongodb 
MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["kgxllm"]
diseases_collection = db["diseases"]

# get the disease
doc = diseases_collection.find_one({"disease": assigned_disease})
drug_map = doc["drug_map"]

# progress bar
total = len(drug_map)
completed = 0

for _, data in drug_map.items():
    q = data.get("questionnaire", {})
    if all(v not in ["", None] for v in q.values()):
        completed += 1

st.write(f"Progress: **{completed} / {total} drugs completed**")
st.progress(completed / total)

def find_next_drug():
    for name, data in drug_map.items():
        q = data.get("questionnaire", {})
        if any(v in ["", None] for v in q.values()): 
            return name
    return None

current_drug = find_next_drug()

# if all drugs are completely annotated 
if current_drug is None:
    st.success("🎉 All drugs are fully annotated!")
    st.stop()

# create the title for this
st.title(f"{assigned_disease} — Drug Annotation")
st.header(f"Drug: **{current_drug}**")

# load questionnaire based on prefilled information
questionnaire = drug_map[current_drug]["questionnaire"]

def yes_no_radio(label, current_val):
    if current_val is True:
        ui_val = "Yes"
    elif current_val is False:
        ui_val = "No"
    else:
        ui_val = ""
    choice = st.radio(label, ["", "Yes", "No"], index=["", "Yes", "No"].index(ui_val))
    return choice

# pre fill information 
def prefilled_select(label, options, current_val):
    if current_val not in options:
        current_val = options[0]
    return st.selectbox(label, options, index=options.index(current_val))

Q1 = prefilled_select(
    "Q1. FDA Status",
    [
        "",
        "FDA_approved_for_[Disease]",
        "FDA_approved_for_other_disease",
        "Not_FDA_approved"
    ],
    questionnaire.get("Q1_FDA_status", "")
)

Q2 = prefilled_select(
    "Q2. Research Status",
    [
        "",
        "FDA_approved_for_[Disease]",
        "irrelevant_drugs",
        "positive_clinical_outcomes",
        "negative_clinical_outcomes",
        "positive_in_vivo_outcomes",
        "negative_in_vivo_outcomes",
        "positive_in_vitro_outcomes",
        "negative_in_vitro_outcomes",
        "rarely_discussed"
    ],
    questionnaire.get("Q2_Research_status", "")
)

Q3 = prefilled_select(
    "Q3. Is this drug of interest?",
    [
        "",
        "Of_interest",
        "Not_of_interest",
        "Have_already_tested"
    ],
    questionnaire.get("Q3_interest", "")
)

# yes/no questions

Q4 = yes_no_radio(
    "Q4. Combination therapy possible?",
    questionnaire.get("Q4_combination_therapy", "")
)

Q5 = yes_no_radio(
    "Q5. Does GPT’s reasoning make sense?",
    questionnaire.get("Q5_reasoning_makes_sense", "")
)

Q7 = yes_no_radio(
    "Q7. Neurotoxicity Concern?",
    questionnaire.get("Q7_neurotoxicity_concern", "")
)

# fill in information 

Q6 = st.text_input( 
    "Q6. Delivery Method Notes",
    value=questionnaire.get("Q6_delivery_method_notes", "")
)

Q8_PMIDs = st.text_area(
    "Q8. Supporting Evidence (PMIDs)",
    value=", ".join(questionnaire.get("Q8_supporting_evidence_pmids", []))
)

Q9_notes = st.text_area(
    "Q9. Additional Notes (Optional)",
    value=questionnaire.get("Q9_note", "")
)


if st.button("Next"):

    new = {
    "Q1_FDA_status": Q1,
    "Q2_Research_status": Q2,
    "Q3_interest": Q3,
    "Q4_combination_therapy": True if Q4 == "Yes" else False if Q4 == "No" else "",
    "Q5_reasoning_makes_sense": True if Q5 == "Yes" else False if Q5 == "No" else "",
    "Q7_neurotoxicity_concern": True if Q7 == "Yes" else False if Q7 == "No" else "",
    "Q6_delivery_method_notes": Q6,
    "Q8_supporting_evidence_pmids": [p.strip() for p in Q8_PMIDs.split(",") if p.strip()],
    "Q9_note": Q9_notes
    }

    # rebuild set only for information that changed 
    updates = {}
    for key, new_val in new.items():
        old_val = questionnaire.get(key, "")
        if new_val != old_val:
            updates[f"drug_map.{current_drug}.questionnaire.{key}"] = new_val

    if updates:
        diseases_collection.update_one(
            {"disease": assigned_disease},
            {"$set": updates}
        )

    # save the information 
    st.success("Saved!")
    st.rerun()
