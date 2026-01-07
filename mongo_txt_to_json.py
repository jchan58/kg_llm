import json
from bson import json_util

with open("pancreatic_cancer_annotations.txt", "r", encoding="utf-8") as f:
    raw_data = f.read()

parsed = json.loads(raw_data, object_hook=json_util.object_hook)
def clean_ids(obj):
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            # Convert ObjectId → string
            if str(type(v)) == "<class 'bson.objectid.ObjectId'>":
                new_obj[k] = str(v)
            else:
                new_obj[k] = clean_ids(v)
        return new_obj

    elif isinstance(obj, list):
        return [clean_ids(i) for i in obj]

    else:
        return obj

cleaned = clean_ids(parsed)
with open("clean_output.json", "w", encoding="utf-8") as f:
    json.dump(cleaned, f, indent=2, ensure_ascii=False)

print("pancreaticcancer_annotation.json")
