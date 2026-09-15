import json

try:
    final_grouped_data = {
        "Pipes": [{"Item_ID": "PROD_0001", "INPUT - Part_Desc": "Pipe", "Category": "Pipes", "Confidence": 0.9}],
        None: [{"Item_ID": "PROD_0002", "INPUT - Part_Desc": "Unknown", "Category": None, "Confidence": None}]
    }

    category_record = {
        "categories": [{"name": k, "item_count": len(v), "sample_items": v[:3]} for k, v in final_grouped_data.items()],
        "source_file": "test.xlsx",
        "total_items": 2
    }

    print("category_record:", category_record)
    serialized = json.dumps(category_record, sort_keys=True)
    print("Serialization OK!")
except Exception as e:
    print("CRASH:", type(e), e)
