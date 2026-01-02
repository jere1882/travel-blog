#!/usr/bin/env python3
"""
Script to normalize image filenames in travel archive folders.

For each trip folder:
1. Renames all images to: img_[trip_id]_001.jpg, img_[trip_id]_002.jpg, etc.
2. Updates all references in BOTH English and Spanish markdown files
3. Preserves file extensions

Usage:
    python normalize_image_names.py              # Dry run
    python normalize_image_names.py --execute   # Actually rename files
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def get_trip_id(md_content: str) -> str:
    """Extract trip_id from markdown frontmatter."""
    match = re.search(r'^trip_id:\s*(.+?)\s*$', md_content, re.MULTILINE)
    return match.group(1).strip() if match else None


def get_image_files(folder: Path) -> List[Path]:
    """Get all image files in the folder."""
    extensions = {'.jpg', '.jpeg', '.png', '.heic', '.JPG', '.JPEG', '.PNG', '.HEIC'}
    return sorted([
        f for f in folder.iterdir()
        if f.is_file() and f.suffix in extensions
    ])


def find_markdown_file(folder: Path) -> Path:
    """Find the .md file in the folder."""
    md_files = list(folder.glob('*.md'))
    return md_files[0] if md_files else None


def normalize_extension(ext: str) -> str:
    """Normalize file extension to lowercase."""
    return ext.lower()


def update_markdown_content(content: str, rename_map: Dict[str, str]) -> Tuple[str, int]:
    """
    Update image references in markdown content.
    Returns (updated_content, reference_count)
    """
    new_content = content
    reference_updates = 0
    
    for old_name, new_name in rename_map.items():
        old_pattern = re.escape(old_name)
        
        # Update ![[image.jpg]] references
        if re.search(rf'!\[\[{old_pattern}\]\]', new_content):
            new_content = re.sub(
                rf'!\[\[{old_pattern}\]\]',
                f'![[{new_name}]]',
                new_content
            )
            reference_updates += 1
        
        # Also update main_image in frontmatter
        if re.search(rf'^main_image:\s*{old_pattern}\s*$', new_content, re.MULTILINE):
            new_content = re.sub(
                rf'^(main_image:\s*){old_pattern}(\s*)$',
                rf'\g<1>{new_name}\g<2>',
                new_content,
                flags=re.MULTILINE
            )
            reference_updates += 1
    
    return new_content, reference_updates


def process_folder(en_folder: Path, es_folder: Path, dry_run: bool = True) -> Tuple[int, int]:
    """
    Process a single trip folder.
    Returns (renamed_count, reference_updates_count)
    """
    en_md_file = find_markdown_file(en_folder)
    if not en_md_file:
        print(f"  Skipping: No .md file found")
        return 0, 0
    
    # Read English markdown content
    try:
        with open(en_md_file, 'r', encoding='utf-8') as f:
            en_content = f.read()
    except Exception as e:
        print(f"  Error reading {en_md_file.name}: {e}")
        return 0, 0
    
    # Get trip_id
    trip_id = get_trip_id(en_content)
    if not trip_id:
        print(f"  Skipping: No trip_id found in frontmatter")
        return 0, 0
    
    # Get all images from English folder (source of truth)
    images = get_image_files(en_folder)
    if not images:
        print(f"  No images to rename")
        return 0, 0
    
    # Build rename mapping
    rename_map: Dict[str, str] = {}  # old_name -> new_name
    counter = 1
    
    for img in images:
        old_name = img.name
        ext = normalize_extension(img.suffix)
        new_name = f"img_{trip_id}_{counter:03d}{ext}"
        
        # Skip if already normalized
        if old_name == new_name:
            counter += 1
            continue
        
        # Handle collision
        while (en_folder / new_name).exists() and new_name not in rename_map.values():
            counter += 1
            new_name = f"img_{trip_id}_{counter:03d}{ext}"
        
        rename_map[old_name] = new_name
        counter += 1
    
    if not rename_map:
        print(f"  All images already normalized ✓")
        return 0, 0
    
    # Update English markdown
    new_en_content, en_refs = update_markdown_content(en_content, rename_map)
    
    # Check for Spanish markdown
    es_md_file = find_markdown_file(es_folder) if es_folder.exists() else None
    es_content = None
    new_es_content = None
    es_refs = 0
    
    if es_md_file:
        try:
            with open(es_md_file, 'r', encoding='utf-8') as f:
                es_content = f.read()
            new_es_content, es_refs = update_markdown_content(es_content, rename_map)
        except Exception as e:
            print(f"    Warning: Could not read Spanish file: {e}")
    
    total_refs = en_refs + es_refs
    
    if dry_run:
        print(f"  [DRY RUN] Would rename {len(rename_map)} images:")
        for old, new in list(rename_map.items())[:5]:
            print(f"    {old} → {new}")
        if len(rename_map) > 5:
            print(f"    ... and {len(rename_map) - 5} more")
        print(f"  [DRY RUN] Would update {en_refs} refs in EN, {es_refs} refs in ES")
        return len(rename_map), total_refs
    
    # Execute renames (use temporary names to avoid collisions)
    temp_suffix = "_TEMP_RENAME_"
    
    # First pass: rename to temporary names
    for old_name in rename_map.keys():
        old_path = en_folder / old_name
        temp_path = en_folder / (old_name + temp_suffix)
        if old_path.exists():
            old_path.rename(temp_path)
    
    # Second pass: rename to final names
    renamed_count = 0
    for old_name, new_name in rename_map.items():
        temp_path = en_folder / (old_name + temp_suffix)
        new_path = en_folder / new_name
        if temp_path.exists():
            temp_path.rename(new_path)
            renamed_count += 1
    
    # Write updated English markdown
    with open(en_md_file, 'w', encoding='utf-8') as f:
        f.write(new_en_content)
    
    # Write updated Spanish markdown if it exists
    if es_md_file and new_es_content:
        with open(es_md_file, 'w', encoding='utf-8') as f:
            f.write(new_es_content)
    
    es_status = f", {es_refs} ES refs" if es_refs > 0 else ""
    print(f"  ✓ Renamed {renamed_count} images, updated {en_refs} EN refs{es_status}")
    return renamed_count, total_refs


def main():
    """Main function."""
    dry_run = '--execute' not in sys.argv
    
    # Get paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    en_archive = project_root / 'travel_atlas' / 'travel_archive'
    es_archive = project_root / 'travel_atlas' / 'travel_archive_es'
    
    if not en_archive.exists():
        print(f"ERROR: Archive not found: {en_archive}")
        sys.exit(1)
    
    print("=" * 60)
    print("IMAGE NAME NORMALIZER")
    print("=" * 60)
    print(f"EN Archive: {en_archive}")
    print(f"ES Archive: {es_archive}")
    print(f"Format: img_[trip_id]_001.jpg, img_[trip_id]_002.jpg, ...")
    print()
    
    if dry_run:
        print("DRY RUN MODE - No files will be renamed.")
        print("Use --execute to actually rename files.")
    else:
        print("EXECUTE MODE - Files will be renamed!")
    print()
    
    # Process each folder
    total_renamed = 0
    total_references = 0
    
    for folder in sorted(en_archive.iterdir()):
        if not folder.is_dir():
            continue
        
        print(f"Processing: {folder.name}")
        es_folder = es_archive / folder.name
        renamed, refs = process_folder(folder, es_folder, dry_run)
        total_renamed += renamed
        total_references += refs
        print()
    
    # Summary
    print("=" * 60)
    print("Summary:")
    print(f"  Images {'to rename' if dry_run else 'renamed'}: {total_renamed}")
    print(f"  References {'to update' if dry_run else 'updated'} (EN + ES): {total_references}")
    print("=" * 60)


if __name__ == '__main__':
    main()
