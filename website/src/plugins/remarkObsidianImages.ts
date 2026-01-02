import { visit } from 'unist-util-visit';
import type { Root, Paragraph, Text, Image } from 'mdast';
import imageManifest from '../data/image_manifest.json';

interface RemarkPluginOptions {
  getImagePath?: (filename: string, file: any) => string;
}

// Type the manifest
const manifest = imageManifest as Record<string, { cdn_url: string; url: string }>;

/**
 * Remark plugin to transform Obsidian-style image embeds
 * ![[image.jpg]] -> standard markdown image with Cloudinary CDN URL
 */
export function remarkObsidianImages(options: RemarkPluginOptions = {}) {
  return (tree: Root, file: any) => {
    // Get the folder from the file path (works for both EN and ES archives)
    const filePath = file.history?.[0] || '';
    const folderMatch = filePath.match(/travel_archive(?:_es)?\/([^/]+)\//);
    const folder = folderMatch ? folderMatch[1] : '';

    visit(tree, 'paragraph', (node: Paragraph, index, parent) => {
      const newChildren: any[] = [];
      let hasChanges = false;

      for (const child of node.children) {
        if (child.type === 'text') {
          const text = (child as Text).value;
          const regex = /!\[\[([^\]]+)\]\]/g;
          let lastIndex = 0;
          let match;

          while ((match = regex.exec(text)) !== null) {
            hasChanges = true;
            
            // Add text before the match
            if (match.index > lastIndex) {
              newChildren.push({
                type: 'text',
                value: text.slice(lastIndex, match.index)
              });
            }

            // Create image node
            const filename = match[1];
            
            // Try to get Cloudinary CDN URL from manifest
            const manifestKey = `${folder}/${filename}`;
            let imagePath: string;
            
            if (manifest[manifestKey]?.cdn_url) {
              // Use Cloudinary CDN URL (auto-format, auto-quality)
              imagePath = manifest[manifestKey].cdn_url;
            } else {
              // Fallback to local path
              const encodedFilename = encodeURIComponent(filename);
              imagePath = `/images/${folder}/${encodedFilename}`;
            }
            
            newChildren.push({
              type: 'image',
              url: imagePath,
              alt: filename,
              title: null
            } as Image);

            lastIndex = regex.lastIndex;
          }

          // Add remaining text
          if (lastIndex < text.length) {
            if (lastIndex === 0) {
              newChildren.push(child);
            } else {
              newChildren.push({
                type: 'text',
                value: text.slice(lastIndex)
              });
            }
          } else if (lastIndex === 0) {
            newChildren.push(child);
          }
        } else {
          newChildren.push(child);
        }
      }

      if (hasChanges) {
        node.children = newChildren;
      }
    });
  };
}

export default remarkObsidianImages;
