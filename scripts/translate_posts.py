#!/usr/bin/env python3
"""
Script to translate English blog posts to Spanish using Google Gemini API.

The English posts in travel_atlas/travel_archive/ are the SOURCE OF TRUTH.
Spanish translations are stored in travel_atlas/travel_archive_es/

Only translates files that:
1. Don't have a Spanish translation yet, OR
2. Have been modified since the last translation

Usage:
    python translate_posts.py              # Dry run - shows what would be translated
    python translate_posts.py --execute    # Actually translate files
    python translate_posts.py --force      # Force re-translate all files
"""

import os
import re
import sys
import json
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai package not installed.")
    print("Run: pip install google-generativeai python-dotenv")
    sys.exit(1)


# Configuration
GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("ERROR: GOOGLE_GEMINI_API_KEY not found in environment or .env file")
    sys.exit(1)

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Translation tracking file
TRANSLATION_CACHE_FILE = '.translation_cache.json'


def get_content_hash(content: str) -> str:
    """Generate a hash of the content for change detection."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def load_translation_cache(project_root: Path) -> Dict:
    """Load the translation cache from disk."""
    cache_path = project_root / TRANSLATION_CACHE_FILE
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_translation_cache(project_root: Path, cache: Dict):
    """Save the translation cache to disk."""
    cache_path = project_root / TRANSLATION_CACHE_FILE
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2)


def translate_with_gemini(content: str, title: str) -> Optional[str]:
    """
    Translate markdown content from English to Spanish using Gemini.
    Preserves markdown formatting and YAML frontmatter structure.
    """
    prompt = f"""You are a professional translator. Translate the following travel blog post from English to neutral Spanish (suitable for Latin American readers, particularly Argentinian, but using neutral Spanish without regional slang).

IMPORTANT RULES:
1. Translate ALL text content naturally and fluently
2. Keep the meaning intact - do not add or remove any information
3. Preserve ALL markdown formatting exactly (![[image.jpg]], ##, *, >, etc.)
4. Preserve the YAML frontmatter structure but translate these fields:
   - title: translate to Spanish
   - DO NOT translate: trip_id, date_from, date_to, duration, countries, cities, social, airline, tags, main_image, main_image_crop, publish
5. Keep all image filenames exactly as they are
6. Preserve any English proper nouns (place names, restaurant names, etc.) but you can add Spanish articles
7. Make the translation sound natural, as if originally written in Spanish
8. Translate captions under images (text starting with *)

Here is the blog post to translate:

---
{content}
---

Provide ONLY the translated content, nothing else. Start directly with the --- of the frontmatter."""

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        if response.text:
            translated = response.text.strip()
            # Clean up any markdown code block wrapping
            if translated.startswith('```'):
                lines = translated.split('\n')
                # Remove first and last lines if they're code block markers
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                translated = '\n'.join(lines)
            return translated
        else:
            print(f"  WARNING: Empty response from Gemini for '{title}'")
            return None
            
    except Exception as e:
        print(f"  ERROR translating '{title}': {e}")
        return None


def needs_translation(
    en_file: Path, 
    es_file: Path, 
    en_content: str, 
    cache: Dict,
    force: bool = False
) -> bool:
    """Check if a file needs translation."""
    if force:
        return True
    
    # If Spanish file doesn't exist, needs translation
    if not es_file.exists():
        return True
    
    # Check if English content has changed since last translation
    file_key = str(en_file.name)
    current_hash = get_content_hash(en_content)
    
    if file_key in cache:
        if cache[file_key].get('en_hash') == current_hash:
            return False  # No changes since last translation
    
    return True


def process_trip_folder(
    en_folder: Path,
    es_folder: Path,
    cache: Dict,
    dry_run: bool = True,
    force: bool = False
) -> tuple[int, int]:
    """
    Process a single trip folder.
    Returns (translated_count, skipped_count)
    """
    # Find markdown file in English folder
    md_files = list(en_folder.glob('*.md'))
    if not md_files:
        return 0, 0
    
    en_md = md_files[0]
    es_md = es_folder / en_md.name
    
    # Read English content
    try:
        with open(en_md, 'r', encoding='utf-8') as f:
            en_content = f.read()
    except Exception as e:
        print(f"  Error reading {en_md}: {e}")
        return 0, 0
    
    # Extract title for logging
    title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', en_content, re.MULTILINE)
    title = title_match.group(1) if title_match else en_folder.name
    
    # Check if translation is needed
    if not needs_translation(en_md, es_md, en_content, cache, force):
        print(f"  ✓ {title} - already translated (no changes)")
        return 0, 1
    
    if dry_run:
        if es_md.exists():
            print(f"  [DRY RUN] Would re-translate: {title}")
        else:
            print(f"  [DRY RUN] Would translate: {title}")
        return 1, 0
    
    # Create Spanish folder if needed
    es_folder.mkdir(parents=True, exist_ok=True)
    
    # Note: Images are NOT duplicated. Spanish pages use the same /images/ path
    # which points to the English archive via the public/images symlink.
    
    # Translate the content
    print(f"  Translating: {title}...")
    translated = translate_with_gemini(en_content, title)
    
    if translated:
        # Write Spanish version
        with open(es_md, 'w', encoding='utf-8') as f:
            f.write(translated)
        
        # Update cache
        file_key = str(en_md.name)
        cache[file_key] = {
            'en_hash': get_content_hash(en_content),
            'translated_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print(f"  ✓ Translated: {title}")
        return 1, 0
    else:
        print(f"  ✗ Failed to translate: {title}")
        return 0, 0


def main():
    """Main function."""
    # Parse arguments
    dry_run = '--execute' not in sys.argv
    force = '--force' in sys.argv
    
    # Get paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    en_archive = project_root / 'travel_atlas' / 'travel_archive'
    es_archive = project_root / 'travel_atlas' / 'travel_archive_es'
    
    if not en_archive.exists():
        print(f"ERROR: English archive not found: {en_archive}")
        sys.exit(1)
    
    print("=" * 60)
    print("TRAVEL BLOG TRANSLATOR (EN → ES)")
    print("=" * 60)
    print(f"Source (EN): {en_archive}")
    print(f"Target (ES): {es_archive}")
    print()
    
    if dry_run:
        print("DRY RUN MODE - No files will be translated.")
        print("Use --execute to actually translate files.")
        print("Use --force to force re-translation of all files.")
    else:
        print("EXECUTE MODE - Files will be translated!")
        if force:
            print("FORCE MODE - All files will be re-translated!")
    print()
    
    # Load translation cache
    cache = load_translation_cache(project_root)
    
    # Process each trip folder
    total_translated = 0
    total_skipped = 0
    
    for folder in sorted(en_archive.iterdir()):
        if not folder.is_dir():
            continue
        
        print(f"Processing: {folder.name}")
        es_folder = es_archive / folder.name
        
        translated, skipped = process_trip_folder(
            folder, es_folder, cache, dry_run, force
        )
        
        total_translated += translated
        total_skipped += skipped
        
        # Rate limiting for API calls
        if not dry_run and translated > 0:
            time.sleep(1)  # Be nice to the API
    
    # Save cache
    if not dry_run:
        save_translation_cache(project_root, cache)
    
    # Summary
    print()
    print("=" * 60)
    print("Summary:")
    print(f"  Posts translated: {total_translated}")
    print(f"  Posts skipped (up-to-date): {total_skipped}")
    print("=" * 60)


if __name__ == '__main__':
    main()

