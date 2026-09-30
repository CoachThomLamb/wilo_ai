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

            # Preserve timestamp from root level with appropriate field name
            if 'finishedAt' in data and timestamp_field:
                new_doc[timestamp_field] = data['finishedAt']

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

def flatten_blocks(collection_name):
    """
    Flatten blocks into a direct exercises array.
    Removes blocks layer, keeps exercises at root level.
    Renames exercise id → instanceId, derives exId from name.
    """
    print(f"\nFlattening blocks in {collection_name} collection...")

    docs = db.collection(collection_name).stream()
    count = 0
    errors = []

    for doc in docs:
        try:
            data = doc.to_dict()
            blocks = data.get('blocks', [])

            if not blocks:
                print(f"  ⚠ {doc.id}: no blocks found, skipping")
                continue

            # Flatten: extract all exercises from blocks into a single array
            exercises = []
            for block in blocks:
                for ex in block.get('exercises', []):
                    # Transform exercise structure:
                    # - id → instanceId
                    # - derive exId from name
                    name = ex.get('name', '')
                    ex_id = ex.get('id')

                    flattened_ex = {
                        'instanceId': ex_id,  # Firestore's id becomes instanceId
                        'exId': name.lower().replace(' ', '-').replace('_', '-'),  # derive from name
                        'name': name,
                        'timed': ex.get('timed', False),
                        'custom_name': ex.get('custom_name'),
                        'note': ex.get('note', ''),
                        'fallback': ex.get('fallback'),
                        'swapped': ex.get('swapped', False),
                        'original': ex.get('original'),
                        'sets': ex.get('sets', [])
                    }

                    # Copy any other fields not explicitly handled
                    for key in ex:
                        if key not in ['id', 'name', 'timed', 'custom_name', 'note', 'fallback', 'swapped', 'original', 'sets']:
                            flattened_ex[key] = ex[key]

                    exercises.append(flattened_ex)

            # Create flattened document
            flattened = {
                'id': data.get('id'),
                'name': data.get('name'),
                'exercises': exercises
            }

            # Preserve timestamp fields
            if 'assignedFor' in data:
                flattened['assignedFor'] = data['assignedFor']
            if 'finishedAt' in data:
                flattened['finishedAt'] = data['finishedAt']

            # Preserve any other fields
            for key in data:
                if key not in ['id', 'name', 'blocks', 'exercises', 'assignedFor', 'finishedAt']:
                    flattened[key] = data[key]

            # Write back to same document (overwrites)
            db.collection(collection_name).document(doc.id).set(flattened)
            print(f"  ✓ {doc.id}: flattened ({len(exercises)} exercises)")
            count += 1
        except Exception as e:
            error_msg = f"  ✗ {doc.id}: {str(e)}"
            print(error_msg)
            errors.append(error_msg)

    print(f"Flattened {count} documents")
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

        # Check required fields (for flattened structure)
        missing = []
        if not data.get('id'):
            missing.append('id')
        if not data.get('name'):
            missing.append('name')
        if 'exercises' not in data:
            missing.append('exercises')
        else:
            # Check exercises have required fields
            for i, ex in enumerate(data.get('exercises', [])):
                if not ex.get('instanceId'):
                    missing.append(f'exercises[{i}].instanceId')
                if not ex.get('exId'):
                    missing.append(f'exercises[{i}].exId')
                if not ex.get('name'):
                    missing.append(f'exercises[{i}].name')
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

    # Phase 1: Migrate programs → assigned and sessions → completed (if needed)
    print("Phase 1: Initial migration (programs/sessions → assigned/completed)")
    programs_count, programs_errors = migrate_collection('programs', 'assigned', timestamp_field='assignedFor')
    all_errors.extend(programs_errors)

    sessions_count, sessions_errors = migrate_collection('sessions', 'completed', timestamp_field='finishedAt')
    all_errors.extend(sessions_errors)

    print(f"\n{'='*60}")
    print(f"Phase 1 Summary:")
    print(f"  assigned: {programs_count} docs")
    print(f"  completed: {sessions_count} docs")
    if all_errors:
        print(f"  total errors: {len(all_errors)}")
    print(f"{'='*60}")

    # Phase 2: Flatten blocks in assigned/completed
    print("\n\nPhase 2: Flatten blocks in assigned/completed collections")
    assigned_flatten_count, assigned_flatten_errors = flatten_blocks('assigned')
    all_errors.extend(assigned_flatten_errors)

    completed_flatten_count, completed_flatten_errors = flatten_blocks('completed')
    all_errors.extend(completed_flatten_errors)

    print(f"\n{'='*60}")
    print(f"Phase 2 Summary:")
    print(f"  assigned: {assigned_flatten_count} docs flattened")
    print(f"  completed: {completed_flatten_count} docs flattened")
    print(f"{'='*60}")

    # Validate flattened data
    print(f"\n{'='*60}")
    print("Validating flattened structure...")
    assigned_valid, assigned_invalid, assigned_failures = validate_collection('assigned', 'assignedFor')
    completed_valid, completed_invalid, completed_failures = validate_collection('completed', 'finishedAt')
    print(f"{'='*60}")

    print(f"\n{'='*60}")
    print(f"Final Validation Summary:")
    print(f"  assigned: {assigned_valid} valid, {assigned_invalid} invalid")
    print(f"  completed: {completed_valid} valid, {completed_invalid} invalid")

    if assigned_invalid == 0 and completed_invalid == 0:
        print(f"\n✓ Migration successful! All documents validated.")
    else:
        print(f"\n⚠ Migration has validation issues. Review failures above.")
    print(f"{'='*60}")
