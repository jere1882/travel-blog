#!/usr/bin/env python3
"""
Syncs travel_archive images to Cloudinary.
Only uploads new/changed images (tracks via manifest).

Usage:
    python sync_to_cloudinary.py              # Dry run
    python sync_to_cloudinary.py --execute   # Actually upload
"""

import cloudinary
import cloudinary.uploader
import hashlib
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

SCRIPT_DIR = Path(__file__).parent
MANIFEST_PATH = SCRIPT_DIR / 'image_manifest.json'
ARCHIVE_PATH = SCRIPT_DIR.parent / 'travel_atlas' / 'travel_archive'
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}


def get_file_hash(path: Path) -> str:
    """Get MD5 hash of file for change detection."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_manifest() -> dict:
    """Load existing manifest or return empty dict."""
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest: dict):
    """Save manifest to JSON file."""
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True))


def sync_images(dry_run: bool = True):
    """
    Sync all images from travel_archive to Cloudinary.
    Only uploads new or changed images.
    """
    # Verify Cloudinary config
    if not os.environ.get('CLOUDINARY_CLOUD_NAME'):
        print("ERROR: Cloudinary credentials not found in .env")
        sys.exit(1)
    
    print(f"Cloud Name: {os.environ.get('CLOUDINARY_CLOUD_NAME')}")
    print(f"Archive Path: {ARCHIVE_PATH}")
    print()
    
    manifest = load_manifest()
    uploaded = 0
    skipped = 0
    errors = 0
    
    # Get all folders
    folders = sorted([f for f in ARCHIVE_PATH.iterdir() if f.is_dir()])
    total_folders = len(folders)
    
    for folder_idx, folder in enumerate(folders, 1):
        folder_name = folder.name
        print(f"[{folder_idx}/{total_folders}] {folder_name}")
        
        # Get all images in folder
        images = sorted([
            f for f in folder.iterdir() 
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        ])
        
        for img_path in images:
            key = f"{folder_name}/{img_path.name}"
            
            try:
                file_hash = get_file_hash(img_path)
            except Exception as e:
                print(f"  ✗ Error reading {img_path.name}: {e}")
                errors += 1
                continue
            
            # Skip if unchanged
            if key in manifest and manifest[key].get('hash') == file_hash:
                skipped += 1
                continue
            
            if dry_run:
                print(f"  → Would upload: {img_path.name}")
                uploaded += 1
                continue
            
            # Upload to Cloudinary
            try:
                # Use folder structure: travel_atlas/folder_name/image_name
                public_id = f"travel_atlas/{folder_name}/{img_path.stem}"
                
                result = cloudinary.uploader.upload(
                    str(img_path),
                    public_id=public_id,
                    overwrite=True,
                    resource_type="image",
                    unique_filename=False,
                    use_filename=True
                )
                
                # Store both raw URL and optimized URL
                manifest[key] = {
                    'hash': file_hash,
                    'public_id': result['public_id'],
                    'url': result['secure_url'],
                    # Auto-format (WebP/AVIF) + auto-quality
                    'cdn_url': result['secure_url'].replace(
                        '/upload/', 
                        '/upload/f_auto,q_auto/'
                    )
                }
                
                print(f"  ✓ Uploaded: {img_path.name}")
                uploaded += 1
                
            except Exception as e:
                print(f"  ✗ Error uploading {img_path.name}: {e}")
                errors += 1
        
        # Save manifest after each folder (in case of interruption)
        if not dry_run and uploaded > 0:
            save_manifest(manifest)
    
    # Final save
    if not dry_run:
        save_manifest(manifest)
    
    # Summary
    print()
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    if dry_run:
        print(f"  Would upload: {uploaded}")
        print(f"  Already synced: {skipped}")
        print(f"  Errors: {errors}")
        print()
        print("Run with --execute to actually upload.")
    else:
        print(f"  Uploaded: {uploaded}")
        print(f"  Skipped (unchanged): {skipped}")
        print(f"  Errors: {errors}")
        print(f"  Manifest saved to: {MANIFEST_PATH}")


def main():
    dry_run = '--execute' not in sys.argv
    
    print("=" * 50)
    print("CLOUDINARY IMAGE SYNC")
    print("=" * 50)
    
    if dry_run:
        print("MODE: DRY RUN (no uploads)")
    else:
        print("MODE: EXECUTE (uploading to Cloudinary)")
    print()
    
    sync_images(dry_run)


if __name__ == '__main__':
    main()




