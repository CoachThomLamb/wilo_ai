#!/usr/bin/env python3
"""
Firestore migration: flatten program/sessions structure

Reads from old 'programs' and 'sessions' collections (which have nested
program + sessions layers), extracts the session data, and writes to new
'assigned' and 'completed' collections (flat structure with just the workout).
"""

import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase (uses GOOGLE_APPLICATION_CREDENTIALS env var)
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

db = firestore.client(database_id='wilo')

def migrate_collection(source_collection, target_collection, timestamp_field=None):
    """
    Migrate from source to target collection.
    Extracts sessions[0] from each document and writes to target.

    timestamp_field: if 'assignedFor', rename program's finishedAt to assignedFor.
                     if 'finishedAt', keep program's finishedAt as finishedAt.
    """
    print(f"\nMigrating {source_collection} → {target_collection}...")

    docs = db.collection(source_collection).stream()
    count = 0

    for doc in docs:
        data = doc.to_dict()
        program = data.get('program', {})
        sessions = data.get('sessions', [])

        if not sessions:
            print(f"  ⚠ {doc.id}: no sessions found, skipping")
            continue

        # Extract first (and only) session
        session = sessions[0]

        # Create new document in target collection with flattened structure
        new_doc = {
            'id': session.get('id'),
            'name': session.get('name'),
            'blocks': session.get('blocks', [])
        }

        # Preserve timestamp from program level with appropriate field name
        if 'finishedAt' in program and timestamp_field:
            new_doc[timestamp_field] = program['finishedAt']

        # Preserve any extra fields from the session
        for key in session:
            if key not in ['id', 'name', 'blocks']:
                new_doc[key] = session[key]

        # Write to new collection (use same doc ID)
        db.collection(target_collection).document(doc.id).set(new_doc)
        print(f"  ✓ {doc.id}: migrated")
        count += 1

    print(f"Migrated {count} documents")
    return count

if __name__ == '__main__':
    print("Starting Firestore migration...")

    # Migrate programs → assigned (rename finishedAt to assignedFor)
    programs_count = migrate_collection('programs', 'assigned', timestamp_field='assignedFor')

    # Migrate sessions → completed (keep finishedAt)
    sessions_count = migrate_collection('sessions', 'completed', timestamp_field='finishedAt')

    print(f"\n✓ Migration complete!")
    print(f"  assigned: {programs_count} docs")
    print(f"  completed: {sessions_count} docs")
