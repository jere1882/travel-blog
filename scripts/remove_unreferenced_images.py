#!/usr/bin/env python3
"""
Script to remove image files that are not referenced in the markdown file
of the same folder.

For each trip folder in travel_atlas/travel_archive/:
1. Finds the .md file
2. Extracts all image references using ![[filename]] syntax
3. Lists all image files (jpg, jpeg, png, heic)
4. Deletes images that are not referenced in the markdown
"""

import os
import re
import sys
from pathlib import Path
from typing import Set, List, Tuple


def extract_image_references(md_content: str) -> Set[str]:
    """
    Extract all image filenames from markdown content.
    Handles both ![[filename]] and ![[filename.ext]] formats.
    """
    # Pattern to match ![[filename]] or ![[filename.ext]]
    pattern = r'!\[\[([^\]]+)\]\]'
    matches = re.findall(pattern, md_content)
    
    # Return set of filenames (normalized)
    return {match.strip() for match in matches}


def get_image_files(folder_path: Path) -> List[Path]:
    """Get all image files (jpg, jpeg, png, heic) in the folder."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.JPG', '.JPEG', '.PNG', '.HEIC'}
    return [
        f for f in folder_path.iterdir()
        if f.is_file() and f.suffix in image_extensions
    ]


def find_markdown_file(folder_path: Path) -> Path:
    """Find the .md file in the folder."""
    md_files = list(folder_path.glob('*.md'))
    if not md_files:
        return None
    if len(md_files) > 1:
        print(f"Warning: Multiple .md files found in {folder_path}, using {md_files[0]}")
    return md_files[0]


def process_trip_folder(folder_path: Path, dry_run: bool = True) -> Tuple[int, int]:
    """
    Process a single trip folder.
    Returns (deleted_count, total_unreferenced_count)
    """
    md_file = find_markdown_file(folder_path)
    if not md_file:
        print(f"Skipping {folder_path.name}: No .md file found")
        return 0, 0
    
    # Read markdown content
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except Exception as e:
        print(f"Error reading {md_file}: {e}")
        return 0, 0
    
    # Extract referenced images
    referenced_images = extract_image_references(md_content)
    
    # Get all image files
    image_files = get_image_files(folder_path)
    
    # Find unreferenced images
    unreferenced = []
    for img_file in image_files:
        # Check if the image filename (with or without path) is referenced
        img_name = img_file.name
        # Also check without extension (in case reference doesn't include extension)
        img_name_no_ext = img_file.stem
        
        is_referenced = (
            img_name in referenced_images or
            img_name_no_ext in referenced_images
        )
        
        if not is_referenced:
            unreferenced.append(img_file)
    
    # Delete unreferenced images
    deleted_count = 0
    for img_file in unreferenced:
        if dry_run:
            print(f"  [DRY RUN] Would delete: {img_file.name}")
        else:
            try:
                img_file.unlink()
                print(f"  Deleted: {img_file.name}")
                deleted_count += 1
            except Exception as e:
                print(f"  Error deleting {img_file.name}: {e}")
    
    return deleted_count, len(unreferenced)


def main():
    """Main function."""
    # Parse command line arguments
    dry_run = '--execute' not in sys.argv
    skip_confirmation = '--yes' in sys.argv
    
    # Get the project root (parent of scripts folder)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    archive_path = project_root / 'travel_atlas' / 'travel_archive'
    
    if not archive_path.exists():
        print(f"Error: Archive path not found: {archive_path}")
        sys.exit(1)
    
    print(f"Scanning trip folders in: {archive_path}")
    if dry_run:
        print("DRY RUN MODE - No files will be deleted. Use --execute to actually delete files.")
    else:
        print("EXECUTE MODE - Files will be deleted!")
        if not skip_confirmation:
            response = input("Are you sure you want to proceed? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                sys.exit(0)
    print()
    
    # Process each trip folder
    total_deleted = 0
    total_unreferenced = 0
    folders_processed = 0
    
    for folder in sorted(archive_path.iterdir()):
        if not folder.is_dir():
            continue
        
        print(f"Processing: {folder.name}")
        deleted, unreferenced = process_trip_folder(folder, dry_run=dry_run)
        
        if unreferenced > 0:
            print(f"  Found {unreferenced} unreferenced image(s)")
        else:
            print(f"  All images are referenced ✓")
        
        total_deleted += deleted
        total_unreferenced += unreferenced
        folders_processed += 1
        print()
    
    # Summary
    print("=" * 60)
    print(f"Summary:")
    print(f"  Folders processed: {folders_processed}")
    print(f"  Unreferenced images found: {total_unreferenced}")
    if not dry_run:
        print(f"  Images deleted: {total_deleted}")
    print("=" * 60)


if __name__ == '__main__':
    main()

