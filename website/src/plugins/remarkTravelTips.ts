import { visit } from 'unist-util-visit';
import type { Root, Blockquote } from 'mdast';
// @ts-ignore - these are available through Astro's dependencies
import { toHast } from 'mdast-util-to-hast';
// @ts-ignore - these are available through Astro's dependencies  
import { toHtml } from 'hast-util-to-html';

/**
 * Remark plugin to transform travel tip syntax
 * 
 * Syntax:
 * > ⭐ Your tip text here
 * 
 * Or:
 * > [!tip]
 * > Your tip text here
 * 
 * Into a styled HTML div with class "travel-tip"
 */
export function remarkTravelTips() {
  return (tree: Root) => {
    visit(tree, 'blockquote', (node: Blockquote, index, parent) => {
      if (!parent || index === undefined) return;

      // Get all text content from the blockquote to check if it's a tip
      const getTextContent = (node: any): string => {
        if (node.type === 'text') {
          return node.value;
        }
        if (node.children) {
          return node.children.map(getTextContent).join('');
        }
        return '';
      };

      const content = node.children.map(getTextContent).join('\n').trim();
      
      // Check if this blockquote starts with 💡, ⭐, or [!tip]
      const tipMatch = content.match(/^(?:💡|⭐|\[!tip\])\s*(?:\n|$)(.*)$/s) || content.match(/^(?:💡|⭐|\[!tip\])\s+(.*)$/s);
      
      if (tipMatch) {
        const tipContent = tipMatch[1].trim();
        
        // Create a new blockquote node with the content (without the marker)
        // We'll process the children to remove the marker from all paragraphs
        const newChildren: any[] = [];
        
        // Process all children to remove markers
        for (const child of node.children) {
          if (child.type === 'paragraph') {
            const para = child as any;
            if (para.children && para.children.length > 0) {
              // Find and remove the marker from any text node in this paragraph
              const cleanedChildren: any[] = [];
              let markerFound = false;
              
              // Check if the entire paragraph is just the marker
              const paraText = para.children.map((c: any) => c.type === 'text' ? c.value : '').join('').trim();
              if (/^(?:💡|⭐|\[!tip\])\s*$/.test(paraText)) {
                // This paragraph is ONLY the marker (with optional whitespace), skip it entirely
                markerFound = true;
                continue;
              }
              
              // Also check if paragraph starts with the marker followed by newline/whitespace
              if (/^(?:💡|⭐|\[!tip\])\s+/.test(paraText) || /^(?:💡|⭐|\[!tip\])\n/.test(paraText)) {
                markerFound = true;
              }
              
              for (const paraChild of para.children) {
                if (paraChild.type === 'text') {
                  let textValue = paraChild.value;
                  // Remove 💡, ⭐, or [!tip] marker (with optional whitespace/newline after)
                  // Try multiple patterns to catch different cases
                  const originalValue = textValue;
                  
                  // Remove markers at the start
                  textValue = textValue.replace(/^(?:💡|⭐|\[!tip\])\s*\n?/, '').trim();
                  textValue = textValue.replace(/^(?:💡|⭐|\[!tip\])\s+/, '').trim();
                  textValue = textValue.replace(/^(?:💡|⭐|\[!tip\])$/, '').trim();
                  
                  // Also remove [!tip] if it appears anywhere in the text (in case it wasn't at the start)
                  if (textValue.includes('[!tip]')) {
                    textValue = textValue.replace(/\[!tip\]/g, '').trim();
                    markerFound = true;
                  }
                  
                  if (textValue !== originalValue) {
                    markerFound = true;
                    // Only add the cleaned text if it's not empty
                    if (textValue) {
                      cleanedChildren.push({ ...paraChild, value: textValue });
                    }
                  } else {
                    cleanedChildren.push(paraChild);
                  }
                } else if (paraChild.type === 'textDirective' || paraChild.type === 'containerDirective') {
                  // Skip directive nodes that might contain [!tip]
                  if (paraChild.name === 'tip') {
                    markerFound = true;
                    continue;
                  }
                  cleanedChildren.push(paraChild);
                } else {
                  cleanedChildren.push(paraChild);
                }
              }
              
              // Only add the paragraph if it has content (and skip if it only had the marker)
              if (cleanedChildren.length > 0) {
                newChildren.push({ ...para, children: cleanedChildren });
              } else if (!markerFound) {
                // Keep empty paragraphs if they didn't have a marker
                newChildren.push(para);
              }
            } else {
              // Empty paragraph, skip it
            }
          } else {
            // Keep non-paragraph children as-is
            newChildren.push(child);
          }
        }
        
        // Convert the children to HTML using mdast-util-to-hast
        let tipHtml = '';
        if (newChildren.length > 0) {
          try {
            const hast = toHast({ type: 'root', children: newChildren } as any, { allowDangerousHtml: false });
            if (hast) {
              tipHtml = toHtml(hast, { allowDangerousHtml: false });
            }
          } catch (e) {
            // Fallback: use the text content
            tipHtml = tipContent;
          }
        } else {
          // Fallback: use the text content
          tipHtml = tipContent;
        }
        
        // Final cleanup: remove any remaining markers from the HTML
        // Remove entire paragraphs that only contain the marker (including HTML-encoded brackets)
        tipHtml = tipHtml.replace(/<p>\s*(?:💡|⭐|\[!tip\]|&#91;!tip&#93;)\s*<\/p>/gi, '');
        tipHtml = tipHtml.replace(/<p>\s*(?:💡|⭐|\[!tip\]|&#91;!tip&#93;)\s*<br\s*\/?>\s*<\/p>/gi, '');
        // Remove markers at the start of paragraphs (with optional whitespace/newline)
        tipHtml = tipHtml.replace(/<p>(?:💡|⭐|\[!tip\]|&#91;!tip&#93;)\s*(?:\n|<br\s*\/?>)?/gi, '<p>');
        tipHtml = tipHtml.replace(/<p>\s*(?:💡|⭐|\[!tip\]|&#91;!tip&#93;)\s+/gi, '<p>');
        // Remove markers anywhere in the text (including HTML entities)
        tipHtml = tipHtml.replace(/(?:💡|⭐|\[!tip\]|&#91;!tip&#93;)/gi, '');
        // Also remove any standalone [!tip] text that might have been rendered (with brackets)
        tipHtml = tipHtml.replace(/\[!tip\]/gi, '');
        tipHtml = tipHtml.replace(/&#91;!tip&#93;/gi, '');
        // Clean up any double spaces, empty paragraphs, or paragraphs with just whitespace
        tipHtml = tipHtml.replace(/<p>\s*<\/p>/gi, '');
        tipHtml = tipHtml.replace(/<p>\s+<\/p>/gi, '');
        // Normalize whitespace but preserve paragraph structure
        tipHtml = tipHtml.replace(/\n\s*\n/g, '\n').trim();
        
        // Create a new HTML node for the tip box
        const tipNode = {
          type: 'html',
          value: `<div class="travel-tip"><div class="travel-tip-content">${tipHtml}</div></div>`
        };

        // Replace the blockquote with the tip box
        parent.children[index] = tipNode as any;
      }
    });
  };
}

export default remarkTravelTips;
