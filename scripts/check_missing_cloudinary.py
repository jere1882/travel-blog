#!/usr/bin/env python3
"""
Check which images are missing from Cloudinary (without uploading).

This script checks Cloudinary API directly to see if images exist,
regardless of manifest status. Useful for detecting images that need
to be uploaded without re-uploading everything.

Usage:
    python check_missing_cloudinary.py              # Check all folders
    python check_missing_cloudinary.py <folder>     # Check specific folder
"""

import cloudinary
import cloudinary.api
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR.parent / '.env')

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

ARCHIVE_PATH = SCRIPT_DIR.parent / 'travel_atlas' / 'travel_archive'
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}


def check_image_exists(public_id: str) -> bool:
    """Check if an image exists in Cloudinary."""
    try:
        cloudinary.api.resource(public_id, resource_type='image')
        return True
    except cloudinary.api.NotFound:
        return False
    except Exception as e:
        # Other errors (permissions, etc.) - assume doesn't exist
        print(f"    Warning: Error checking {public_id}: {e}")
        return False


def check_folder(folder: Path):
    """Check all images in a folder."""
    folder_name = folder.name
    print(f"\n[{folder_name}]")
    
    # Get all images in folder
    images = sorted([
        f for f in folder.iterdir() 
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ])
    
    if not images:
        print("  No images found")
        return 0, 0
    
    missing = []
    existing = []
    
    for img_path in images:
        # Construct public_id as Cloudinary would have it
        public_id = f"travel_atlas/{folder_name}/{img_path.stem}"
        
        if check_image_exists(public_id):
            existing.append(img_path.name)
        else:
            missing.append(img_path.name)
    
    # Report results
    if missing:
        print(f"  ✗ Missing from Cloudinary ({len(missing)}):")
        for img in missing:
            print(f"    - {img}")
    
    if existing:
        print(f"  ✓ Already in Cloudinary ({len(existing)})")
    
    if not missing:
        print(f"  ✓ All {len(existing)} images are in Cloudinary")
    
    return len(missing), len(existing)


def main():
    """Main function."""
    # Check for specific folder argument
    target_folder = None
    for arg in sys.argv[1:]:
        if not arg.endswith('.py'):
            target_folder = arg
            break
    
    # Verify Cloudinary config
    if not os.environ.get('CLOUDINARY_CLOUD_NAME'):
        print("ERROR: Cloudinary credentials not found in .env")
        sys.exit(1)
    
    print("=" * 60)
    print("CHECK MISSING CLOUDINARY IMAGES")
    print("=" * 60)
    print(f"Cloud Name: {os.environ.get('CLOUDINARY_CLOUD_NAME')}")
    print(f"Archive Path: {ARCHIVE_PATH}")
    print()
    print("Checking Cloudinary API directly (no uploads)...")
    print()
    
    total_missing = 0
    total_existing = 0
    
    if target_folder:
        # Check specific folder
        folder = ARCHIVE_PATH / target_folder
        if not folder.exists() or not folder.is_dir():
            print(f"ERROR: Folder not found: {folder}")
            sys.exit(1)
        
        missing, existing = check_folder(folder)
        total_missing += missing
        total_existing += existing
    else:
        # Check all folders
        folders = sorted([f for f in ARCHIVE_PATH.iterdir() if f.is_dir()])
        total_folders = len(folders)
        
        for folder_idx, folder in enumerate(folders, 1):
            missing, existing = check_folder(folder)
            total_missing += missing
            total_existing += existing
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Missing from Cloudinary: {total_missing}")
    print(f"  Already in Cloudinary: {total_existing}")
    print(f"  Total images checked: {total_missing + total_existing}")
    print()
    if total_missing > 0:
        print("To upload missing images, run:")
        if target_folder:
            print(f"  python scripts/sync_to_cloudinary.py --execute")
        else:
            print(f"  python scripts/sync_to_cloudinary.py --execute")
    else:
        print("✓ All images are in Cloudinary!")


if __name__ == '__main__':
    main()

