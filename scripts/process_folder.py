#!/usr/bin/env python3
"""
Unified image processing script for a single travel archive folder.

Operations (in order):
1. Remove unreferenced images (from Cloudinary and disk)
2. Normalize image names to convention: img_[trip_id]_XXX.jpg/png
3. Resize images that are too large (max 2000px on longest side)
4. Upload new/changed images to Cloudinary

Usage:
    python process_folder.py <folder_path>              # Dry run
    python process_folder.py <folder_path> --execute    # Actually execute
    
Example:
    python process_folder.py travel_atlas/travel_archive/2025_12_21_rio_angra_dos_reis
    python process_folder.py travel_atlas/travel_archive/2025_12_21_rio_angra_dos_reis --execute
"""

import cloudinary
import cloudinary.uploader
import cloudinary.api
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dotenv import load_dotenv

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: PIL not installed. Image resizing will be skipped.")
    print("Install with: pip install Pillow")

# Load environment variables
SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR.parent / '.env')

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

# Constants
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
MAX_IMAGE_SIZE = 2000  # Max pixels on longest side
MANIFEST_PATH = SCRIPT_DIR.parent / 'website' / 'src' / 'data' / 'image_manifest.json'


def load_manifest() -> dict:
    """Load existing manifest or return empty dict."""
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest: dict):
    """Save manifest to JSON file."""
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True))


def get_file_hash(path: Path) -> str:
    """Get MD5 hash of file for change detection."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def extract_image_references(md_content: str) -> Set[str]:
    """Extract all image filenames from markdown content."""
    pattern = r'!\[\[([^\]]+)\]\]'
    matches = re.findall(pattern, md_content)
    return {match.strip() for match in matches}


def get_trip_id(md_content: str) -> str:
    """Extract trip_id from markdown frontmatter."""
    match = re.search(r'^trip_id:\s*(.+?)\s*$', md_content, re.MULTILINE)
    return match.group(1).strip() if match else None


def find_markdown_file(folder: Path) -> Path:
    """Find the .md file in the folder."""
    md_files = list(folder.glob('*.md'))
    return md_files[0] if md_files else None


def get_image_files(folder: Path) -> List[Path]:
    """Get all image files in the folder."""
    return sorted([
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in {e.lower() for e in IMAGE_EXTENSIONS}
    ])


# =============================================================================
# STEP 1: Remove unreferenced images
# =============================================================================

def remove_unreferenced_images(
    folder: Path, 
    folder_name: str,
    md_content: str, 
    manifest: dict, 
    dry_run: bool
) -> Tuple[int, int]:
    """
    Remove images not referenced in markdown from disk and Cloudinary.
    Returns (disk_removed, cloud_removed)
    """
    print("\n[Step 1] Checking for unreferenced images...")
    
    referenced_images = extract_image_references(md_content)
    image_files = get_image_files(folder)
    
    disk_removed = 0
    cloud_removed = 0
    
    for img_file in image_files:
        img_name = img_file.name
        
        if img_name not in referenced_images:
            manifest_key = f"{folder_name}/{img_name}"
            
            if dry_run:
                print(f"  Would remove: {img_name}")
                disk_removed += 1
                if manifest_key in manifest:
                    print(f"    → Also from Cloudinary: {manifest[manifest_key].get('public_id', 'N/A')}")
                    cloud_removed += 1
            else:
                # Remove from Cloudinary first
                if manifest_key in manifest:
                    public_id = manifest[manifest_key].get('public_id')
                    if public_id:
                        try:
                            cloudinary.uploader.destroy(public_id)
                            print(f"  ✓ Removed from Cloudinary: {public_id}")
                            cloud_removed += 1
                        except Exception as e:
                            print(f"  ✗ Error removing from Cloudinary: {e}")
                    del manifest[manifest_key]
                
                # Remove from disk
                try:
                    img_file.unlink()
                    print(f"  ✓ Removed from disk: {img_name}")
                    disk_removed += 1
                except Exception as e:
                    print(f"  ✗ Error removing from disk: {e}")
    
    if disk_removed == 0:
        print("  All images are referenced ✓")
    
    return disk_removed, cloud_removed


# =============================================================================
# STEP 2: Normalize image names
# =============================================================================

def normalize_image_names(
    folder: Path,
    folder_name: str,
    md_file: Path,
    md_content: str,
    trip_id: str,
    manifest: dict,
    dry_run: bool
) -> Tuple[str, int, Dict[str, str]]:
    """
    Rename images to follow convention: img_[trip_id]_XXX.jpg/png
    Returns (updated_md_content, renamed_count, rename_map)
    """
    print("\n[Step 2] Normalizing image names...")
    
    images = get_image_files(folder)
    if not images:
        print("  No images to process")
        return md_content, 0, {}
    
    # Build rename mapping
    rename_map: Dict[str, str] = {}
    
    # First, find the highest existing number
    existing_numbers = set()
    pattern = re.compile(rf'^img_{re.escape(trip_id)}_(\d+)\.(jpg|jpeg|png)$', re.IGNORECASE)
    
    for img in images:
        match = pattern.match(img.name)
        if match:
            existing_numbers.add(int(match.group(1)))
    
    # Assign new numbers to non-conforming images
    next_number = max(existing_numbers, default=0) + 1
    
    for img in images:
        old_name = img.name
        
        # Check if already normalized
        if pattern.match(old_name):
            continue
        
        # Create new name
        ext = img.suffix.lower()
        if ext == '.jpeg':
            ext = '.jpg'
        
        new_name = f"img_{trip_id}_{next_number:03d}{ext}"
        
        # Avoid collision
        while (folder / new_name).exists() or new_name in rename_map.values():
            next_number += 1
            new_name = f"img_{trip_id}_{next_number:03d}{ext}"
        
        rename_map[old_name] = new_name
        next_number += 1
    
    if not rename_map:
        print("  All images already follow naming convention ✓")
        return md_content, 0, {}
    
    # Update markdown content
    new_md_content = md_content
    for old_name, new_name in rename_map.items():
        old_pattern = re.escape(old_name)
        new_md_content = re.sub(rf'!\[\[{old_pattern}\]\]', f'![[{new_name}]]', new_md_content)
        new_md_content = re.sub(
            rf'^(main_image:\s*){old_pattern}(\s*)$',
            rf'\g<1>{new_name}\g<2>',
            new_md_content,
            flags=re.MULTILINE
        )
    
    if dry_run:
        print(f"  Would rename {len(rename_map)} images:")
        for old, new in list(rename_map.items())[:5]:
            print(f"    {old} → {new}")
        if len(rename_map) > 5:
            print(f"    ... and {len(rename_map) - 5} more")
    else:
        # Execute renames using temporary names to avoid collisions
        temp_suffix = "_TEMP_RENAME_"
        
        # First pass: rename to temporary names
        for old_name in rename_map.keys():
            old_path = folder / old_name
            temp_path = folder / (old_name + temp_suffix)
            if old_path.exists():
                old_path.rename(temp_path)
        
        # Second pass: rename to final names
        for old_name, new_name in rename_map.items():
            temp_path = folder / (old_name + temp_suffix)
            new_path = folder / new_name
            if temp_path.exists():
                temp_path.rename(new_path)
                print(f"  ✓ Renamed: {old_name} → {new_name}")
        
        # Update manifest keys
        for old_name, new_name in rename_map.items():
            old_key = f"{folder_name}/{old_name}"
            new_key = f"{folder_name}/{new_name}"
            if old_key in manifest:
                # Update manifest entry with new key
                entry = manifest.pop(old_key)
                # Update public_id in Cloudinary
                old_public_id = entry.get('public_id')
                if old_public_id:
                    new_public_id = f"travel_atlas/{folder_name}/{Path(new_name).stem}"
                    try:
                        # Rename in Cloudinary by re-uploading
                        cloudinary.uploader.rename(old_public_id, new_public_id)
                        entry['public_id'] = new_public_id
                        entry['url'] = entry['url'].replace(old_public_id, new_public_id)
                        entry['cdn_url'] = entry['cdn_url'].replace(old_public_id, new_public_id)
                    except Exception as e:
                        print(f"    Warning: Could not rename in Cloudinary: {e}")
                        # Remove hash to force re-upload
                        entry.pop('hash', None)
                manifest[new_key] = entry
        
        # Write updated markdown
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(new_md_content)
        print(f"  ✓ Updated markdown file")
    
    return new_md_content, len(rename_map), rename_map


# =============================================================================
# STEP 3: Resize large images
# =============================================================================

def resize_large_images(folder: Path, dry_run: bool) -> int:
    """
    Resize images larger than MAX_IMAGE_SIZE pixels.
    Returns number of images resized.
    """
    print("\n[Step 3] Checking for oversized images...")
    
    if not HAS_PIL:
        print("  Skipped (PIL not installed)")
        return 0
    
    images = get_image_files(folder)
    resized_count = 0
    
    for img_path in images:
        try:
            with Image.open(img_path) as img:
                width, height = img.size
                max_dim = max(width, height)
                
                if max_dim <= MAX_IMAGE_SIZE:
                    continue
                
                # Calculate new dimensions
                ratio = MAX_IMAGE_SIZE / max_dim
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                
                if dry_run:
                    print(f"  Would resize: {img_path.name} ({width}x{height} → {new_width}x{new_height})")
                    resized_count += 1
                else:
                    # Resize and save
                    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Preserve EXIF data if possible
                    exif = img.info.get('exif')
                    if exif:
                        resized.save(img_path, quality=90, exif=exif)
                    else:
                        resized.save(img_path, quality=90)
                    
                    print(f"  ✓ Resized: {img_path.name} ({width}x{height} → {new_width}x{new_height})")
                    resized_count += 1
                    
        except Exception as e:
            print(f"  ✗ Error processing {img_path.name}: {e}")
    
    if resized_count == 0:
        print(f"  All images are within size limit ({MAX_IMAGE_SIZE}px) ✓")
    
    return resized_count


# =============================================================================
# STEP 4: Upload to Cloudinary
# =============================================================================

def upload_to_cloudinary(
    folder: Path,
    folder_name: str,
    manifest: dict,
    dry_run: bool
) -> Tuple[int, int]:
    """
    Upload new/changed images to Cloudinary.
    Returns (uploaded_count, skipped_count)
    """
    print("\n[Step 4] Syncing to Cloudinary...")
    
    images = get_image_files(folder)
    uploaded = 0
    skipped = 0
    
    for img_path in images:
        key = f"{folder_name}/{img_path.name}"
        
        try:
            file_hash = get_file_hash(img_path)
        except Exception as e:
            print(f"  ✗ Error reading {img_path.name}: {e}")
            continue
        
        # Skip if unchanged
        if key in manifest and manifest[key].get('hash') == file_hash:
            skipped += 1
            continue
        
        if dry_run:
            if key in manifest:
                print(f"  Would re-upload (changed): {img_path.name}")
            else:
                print(f"  Would upload (new): {img_path.name}")
            uploaded += 1
            continue
        
        # Upload to Cloudinary
        try:
            public_id = f"travel_atlas/{folder_name}/{img_path.stem}"
            
            result = cloudinary.uploader.upload(
                str(img_path),
                public_id=public_id,
                overwrite=True,
                resource_type="image",
                unique_filename=False,
                use_filename=True
            )
            
            manifest[key] = {
                'hash': file_hash,
                'public_id': result['public_id'],
                'url': result['secure_url'],
                'cdn_url': result['secure_url'].replace('/upload/', '/upload/f_auto,q_auto/')
            }
            
            print(f"  ✓ Uploaded: {img_path.name}")
            uploaded += 1
            
        except Exception as e:
            print(f"  ✗ Error uploading {img_path.name}: {e}")
    
    if uploaded == 0 and skipped > 0:
        print(f"  All {skipped} images already synced ✓")
    
    return uploaded, skipped


# =============================================================================
# MAIN
# =============================================================================

def process_folder(folder_path: str, dry_run: bool = True):
    """Process a single folder through all steps."""
    
    # Resolve folder path
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    if folder_path.startswith('travel_atlas'):
        folder = project_root / folder_path
    else:
        folder = Path(folder_path)
    
    if not folder.exists():
        print(f"ERROR: Folder not found: {folder}")
        sys.exit(1)
    
    if not folder.is_dir():
        print(f"ERROR: Not a directory: {folder}")
        sys.exit(1)
    
    folder_name = folder.name
    
    print("=" * 60)
    print("UNIFIED IMAGE PROCESSOR")
    print("=" * 60)
    print(f"Folder: {folder}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print()
    
    # Find and read markdown file
    md_file = find_markdown_file(folder)
    if not md_file:
        print("ERROR: No markdown file found in folder")
        sys.exit(1)
    
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    trip_id = get_trip_id(md_content)
    if not trip_id:
        print("ERROR: No trip_id found in markdown frontmatter")
        sys.exit(1)
    
    print(f"Markdown file: {md_file.name}")
    print(f"Trip ID: {trip_id}")
    
    # Load manifest
    manifest = load_manifest()
    
    # Stats tracking
    stats = {
        'unreferenced_removed': 0,
        'cloud_removed': 0,
        'renamed': 0,
        'resized': 0,
        'uploaded': 0,
        'skipped': 0
    }
    
    # Step 1: Remove unreferenced images
    disk_removed, cloud_removed = remove_unreferenced_images(
        folder, folder_name, md_content, manifest, dry_run
    )
    stats['unreferenced_removed'] = disk_removed
    stats['cloud_removed'] = cloud_removed
    
    # Reload md content and images after removal
    if not dry_run and disk_removed > 0:
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
    
    # Step 2: Normalize image names
    md_content, renamed, rename_map = normalize_image_names(
        folder, folder_name, md_file, md_content, trip_id, manifest, dry_run
    )
    stats['renamed'] = renamed
    
    # Step 3: Resize large images
    resized = resize_large_images(folder, dry_run)
    stats['resized'] = resized
    
    # Step 4: Upload to Cloudinary
    uploaded, skipped = upload_to_cloudinary(folder, folder_name, manifest, dry_run)
    stats['uploaded'] = uploaded
    stats['skipped'] = skipped
    
    # Save manifest
    if not dry_run:
        save_manifest(manifest)
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if dry_run:
        print("  [DRY RUN] Would have:")
        print(f"    - Removed {stats['unreferenced_removed']} unreferenced images")
        print(f"    - Removed {stats['cloud_removed']} from Cloudinary")
        print(f"    - Renamed {stats['renamed']} images")
        print(f"    - Resized {stats['resized']} images")
        print(f"    - Uploaded {stats['uploaded']} images")
        print(f"    - Skipped {stats['skipped']} unchanged images")
        print()
        print("Run with --execute to apply changes.")
    else:
        print(f"  Unreferenced images removed: {stats['unreferenced_removed']}")
        print(f"  Removed from Cloudinary: {stats['cloud_removed']}")
        print(f"  Images renamed: {stats['renamed']}")
        print(f"  Images resized: {stats['resized']}")
        print(f"  Images uploaded: {stats['uploaded']}")
        print(f"  Images unchanged: {stats['skipped']}")
        print(f"  Manifest saved to: {MANIFEST_PATH}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    folder_path = sys.argv[1]
    dry_run = '--execute' not in sys.argv
    
    process_folder(folder_path, dry_run)


if __name__ == '__main__':
    main()

