// @ts-check
import { defineConfig } from 'astro/config';
import remarkObsidianImages from './src/plugins/remarkObsidianImages.ts';
import remarkTravelTips from './src/plugins/remarkTravelTips.ts';
import react from '@astrojs/react';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// https://astro.build/config
export default defineConfig({
  markdown: {
    remarkPlugins: [remarkObsidianImages, remarkTravelTips],
  },

  integrations: [react()],
  
  server: {
    port: 4321,
    host: true
  },
  
  // Watch markdown files outside the website directory
  vite: {
    server: {
      port: 4321,
      watch: {
        // Explicitly watch the travel archive directories
        ignored: [
          '**/node_modules/**',
          '**/.git/**',
          '**/.astro/cache/**',
          // Don't ignore travel archive directories
          '!**/travel_atlas/travel_archive/**',
          '!**/travel_atlas/travel_archive_es/**'
        ]
      },
      // Add the parent directory to the watch list
      fs: {
        allow: ['..']
      }
    }
  }
});