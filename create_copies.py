import streamlit as st
from pymongo import MongoClient
import json
import os

MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["kgxllm"]
collection = db["diseases"]

def upload_disease_for_annotator(disease, annotator):
    """Create a copy of disease pre-annotations for a specific annotator."""
    jsonl_file = os.path.join("new_drug_results", f"{disease}.pre_annotated.jsonl")
    annotator = annotator.strip().lower().replace(" ", "_")
    disease_key = f"{disease.strip().lower()}_{annotator}"

    drug_map = {}

    with open(jsonl_file, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            drug_name = obj.get("drug")
            drug_map[drug_name] = obj

    disease_doc = {
        "disease": disease_key,
        "parent_disease": disease.strip().lower(),
        "annotator": annotator,
        "drug_map": drug_map
    }

    collection.update_one(
        {"disease": disease_key},
        {"$set": disease_doc},
        upsert=True
    )

    print(f"Uploaded {disease_key} with {len(drug_map)} drugs.")

if __name__ == "__main__":
    upload_disease_for_annotator("glioblastoma", "betty")
    upload_disease_for_annotator("glioblastoma", "hasan")