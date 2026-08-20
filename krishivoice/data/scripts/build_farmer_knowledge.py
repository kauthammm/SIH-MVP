"""Build farmer knowledge index from CSV records — run to refresh stats."""
from app.services.farmer_knowledge import build_knowledge_index
import json

if __name__ == "__main__":
    idx = build_knowledge_index()
    print(json.dumps(idx, indent=2, default=str))
    print(f"\nIndexed {idx['total_farmers']} farmers, {idx['total_parcels']} parcels.")
