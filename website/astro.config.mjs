// @ts-check
import { defineConfig } from 'astro/config';
import remarkObsidianImages from './src/plugins/remarkObsidianImages.ts';

import react from '@astrojs/react';

// https://astro.build/config
export default defineConfig({
  markdown: {
    remarkPlugins: [remarkObsidianImages],
  },

  integrations: [react()],
});