
import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

@dataclass
class BoardMember:
    """A board member or executive."""
    name: str
    title: str
    committees: List[str]
    bio: str
    is_independent: bool
    tenure_years: int

def deduplicate_directors(api_directors: List[Dict]) -> List[BoardMember]:
    unique_members: Dict[str, BoardMember] = {}
    
    # Sort by name length descending to ensure full names act as master records
    sorted_directors = sorted(api_directors, key=lambda x: len(x.get('name', '')), reverse=True)

    for d in sorted_directors:
        name = d.get('name', 'Unknown').strip()
        if not name or name == 'Unknown':
            continue
            
        title = d.get('position', '') or ""
        qualifications = d.get('qualificationsAndExperience', [])
        bio_text = ", ".join(qualifications) if qualifications else ""
        committees_data = d.get('committeeMemberships', [])
        clean_committees = []
        for c in committees_data:
            c_name = c if isinstance(c, str) else c.get('name', '')
            if c_name:
                clean_committees.append(c_name)
        
        # 1. Normalize name for mapping
        # Remove honorifics
        clean_name = re.sub(r'^(Mr\.|Ms\.|Mrs\.|Dr\.|Messrs\.)\s+', '', name, flags=re.IGNORECASE)
        
        # 2. Find existing match
        existing_key = None
        for key in list(unique_members.keys()):
            # A match occurs if:
            # - One name is a subset of the other (e.g., "Greg Penner" vs "Gregory B. Penner")
            # - They share the same surname and one is just an honorific snippet (e.g., "Mr. Flynn" vs "Tim Flynn")
            
            # Use space-separated parts for smarter matching
            key_parts = set(key.lower().replace('.', '').split())
            name_parts = set(clean_name.lower().replace('.', '').split())
            
            # Intersection check: if surnames match and one is a subset, it's a match
            surname = clean_name.split()[-1].lower()
            existing_surname = key.split()[-1].lower()
            
            if surname == existing_surname:
                # If surnames match, check if one set of name parts is a subset of the other
                if name_parts.issubset(key_parts) or key_parts.issubset(name_parts):
                    existing_key = key
                    break
        
        current_member = BoardMember(
            name=name,
            title=title,
            bio=bio_text,
            is_independent=bool(d.get('isIndependent')),
            tenure_years=0,
            committees=clean_committees
        )

        if existing_key:
            existing = unique_members[existing_key]
            # MERGE LOGIC:
            # Always keep the longest name as the key
            master_name = name if len(name) > len(existing.name) else existing.name
            
            # Combine committees (set for uniqueness)
            merged_committees = list(set(existing.committees + clean_committees))
            # Keep longer title/bio
            best_title = title if len(title) > len(existing.title) else existing.title
            best_bio = bio_text if len(bio_text) > len(existing.bio) else existing.bio
            
            # Update key if we found a better name
            if len(name) > len(existing.name):
                unique_members.pop(existing_key)
                unique_members[clean_name] = current_member
            
            # Apply merged data to the entry in the map
            target = unique_members[clean_name if len(name) > len(existing.name) else existing_key]
            target.name = master_name
            target.committees = merged_committees
            target.title = best_title
            target.bio = best_bio
        else:
            unique_members[clean_name] = current_member

    return list(unique_members.values())

# Test Data based on the logs
test_directors = [
    {"name": "Greg Penner", "position": "Non-Executive Chairman", "committeeMemberships": []},
    {"name": "Gregory B. Penner", "position": "NON-EXECUTIVE CHAIRMAN", "committeeMemberships": ["Executive Committee"]},
    {"name": "Tim Flynn", "position": "Retired Chairman and CEO, KPMG", "committeeMemberships": []},
    {"name": "Mr. Flynn", "position": "Chairman of the Board", "committeeMemberships": []},
    {"name": "John Furner", "position": "Executive Vice President, President and CEO, Walmart U.S.", "committeeMemberships": []},
    {"name": "Kath McLay", "position": "Executive Vice President, President and CEO, Walmart International", "committeeMemberships": []}
]

print("--- Original Count: ", len(test_directors))
deduped = deduplicate_directors(test_directors)
print("--- Deduped Count: ", len(deduped))

for m in deduped:
    print(f"Name: {m.name} | Title: {m.title} | Committees: {m.committees}")
