import json
import streamlit as st
from pymongo import MongoClient

MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI)
db = client["kgxllm"]
collection = db["diseases"]
jsonl_file = "drug_results\glioblastoma.pre_annotation.jsonl"

drug_map = {}
with open(jsonl_file, "r", encoding="utf-8") as file:
    for line in file: 
        line = line.strip()
        if not line: 
            continue 

        object = json.loads(line)
        drug_name = object.get("drug")
        drug_map[drug_name] = object 

glioblastoma_doc = {
    "disease": object['disease'], 
    "drug_map": drug_map
}

collection.update_one(
    {"disease": "Glioblastoma"},
    {"$set": glioblastoma_doc},
    upsert=True
)
print(f"Uploaded Glioblastoma with {len(drug_map)} drugs.")
