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
    errors = []

    for doc in docs:
        try:
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
        except Exception as e:
            error_msg = f"  ✗ {doc.id}: {str(e)}"
            print(error_msg)
            errors.append(error_msg)

    print(f"Migrated {count} documents")
    if errors:
        print(f"  {len(errors)} errors encountered")
    return count, errors

def validate_collection(target_collection, timestamp_field):
    """
    Validate all documents in the target collection.
    Check for required fields and report verbose success/failure per document.
    """
    print(f"\nValidating {target_collection} collection...")

    docs = db.collection(target_collection).stream()
    valid_count = 0
    invalid_count = 0
    failures = []

    for doc in docs:
        data = doc.to_dict()
        if data is None:
            print(f"  ✗ {doc.id}: document is empty")
            invalid_count += 1
            failures.append(f"{doc.id}: empty document")
            continue

        # Check required fields
        missing = []
        if not data.get('id'):
            missing.append('id')
        if not data.get('name'):
            missing.append('name')
        if 'blocks' not in data:
            missing.append('blocks')
        if timestamp_field and timestamp_field not in data:
            missing.append(timestamp_field)

        if missing:
            print(f"  ✗ {doc.id}: missing fields {missing}")
            invalid_count += 1
            failures.append(f"{doc.id}: missing {', '.join(missing)}")
        else:
            print(f"  ✓ {doc.id}: valid ({data.get('name')})")
            valid_count += 1

    print(f"Validation complete: {valid_count} valid, {invalid_count} invalid")
    if failures:
        print(f"  Failures:")
        for failure in failures:
            print(f"    - {failure}")
    return valid_count, invalid_count, failures


if __name__ == '__main__':
    print("Starting Firestore migration...\n")

    all_errors = []

    # Migrate programs → assigned (rename finishedAt to assignedFor)
    programs_count, programs_errors = migrate_collection('programs', 'assigned', timestamp_field='assignedFor')
    all_errors.extend(programs_errors)

    # Migrate sessions → completed (keep finishedAt)
    sessions_count, sessions_errors = migrate_collection('sessions', 'completed', timestamp_field='finishedAt')
    all_errors.extend(sessions_errors)

    print(f"\n{'='*60}")
    print(f"Migration Summary:")
    print(f"  assigned: {programs_count} docs")
    print(f"  completed: {sessions_count} docs")
    if all_errors:
        print(f"  total errors: {len(all_errors)}")
    print(f"{'='*60}")

    # Validate migrated data
    print(f"\n{'='*60}")
    assigned_valid, assigned_invalid, assigned_failures = validate_collection('assigned', 'assignedFor')
    completed_valid, completed_invalid, completed_failures = validate_collection('completed', 'finishedAt')
    print(f"{'='*60}")

    print(f"\n{'='*60}")
    print(f"Validation Summary:")
    print(f"  assigned: {assigned_valid} valid, {assigned_invalid} invalid")
    print(f"  completed: {completed_valid} valid, {completed_invalid} invalid")

    if assigned_invalid == 0 and completed_invalid == 0:
        print(f"\n✓ Migration successful! All documents validated.")
    else:
        print(f"\n⚠ Migration has validation issues. Review failures above.")
    print(f"{'='*60}")
