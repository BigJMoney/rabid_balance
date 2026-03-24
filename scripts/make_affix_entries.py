# Input CSV file; output JSON files formatted as Apotheosis loot affic entry
import sys
import csv
import json


def csv_to_dict(file_path):
    """Converts a CSV file to a list of dictionaries."""
    data = []
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            data.append(row)
    return data

def build_affix_entry(data):
    """Converts a raw table entry to a valid affix entry"""
    affix_entry = {}
    valid_entry = False
    affix_entry["type"] = "apotheosis:affix_loot_entry"
    affix_entry["stack"] = {}
    modname = data["mod"]
    affix_entry["stack"]["count"] = 1
    affix_entry["stack"]["id"] =  modname + ":" + data["id"]

    # Global weight pattern
    global_weight = data.get("weight")
    if global_weight or global_weight == 0:
        affix_entry["weight"] = global_weight
        return affix_entry

    # Tiered weight pattern
    affix_entry["weights"] = {}
    tiers = ["haven", "frontier", "ascent", "summit", "pinnacle"]
    for tier in tiers:
        tweight = data.get(f"{tier}_weight")
        if tweight:
            valid_entry = True
            tweight = int(tweight)
            affix_entry["weights"][tier] = {}
            tquality = data.get("{tier}_quality")
            if tquality:
                tquality = float(tquality)
                affix_entry["weights"][tier]["quality"] = tquality
            affix_entry["weights"][tier]["weight"] = tweight
    return affix_entry if valid_entry else None

if __name__ == "__main__":
    filename = sys.argv[1]
    table = csv_to_dict(filename)

    for rawentry in table:
        affix_entry = build_affix_entry(rawentry)
        if affix_entry:
            jsonified_aentry = json.dumps(affix_entry, indent=4)
            outfilename = rawentry["id"] + ".json"
            print(f"{outfilename}...")
            with open(outfilename, 'w') as outfile:
                outfile.write(jsonified_aentry)
        else:
            print(f"Entry {rawentry['id']} was empty")
