import streamlit as st
from pymongo import MongoClient
import json
import os

MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["kgxllm"]
collection = db["diseases"]

def upload_disease(disease):
    jsonl_file = os.path.join("new_drug_results", f"{disease}.pre_annotated.jsonl")
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
        "disease": disease.strip().lower(),
        "drug_map": drug_map
    }
    collection.update_one(
        {"disease": disease.strip().lower()},
        {"$set": disease_doc},
        upsert=True
    )

    print(f"Uploaded {disease} with {len(drug_map)} drugs.")


if __name__ == "__main__":
    upload_disease("pancreaticcancer")  
