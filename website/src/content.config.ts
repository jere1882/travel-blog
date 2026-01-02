import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// Shared schema for trip posts (both EN and ES)
const tripSchema = z.object({
  title: z.string(),
  trip_id: z.string(),
  date_from: z.string(),
  date_to: z.string(),
  duration: z.string(),
  countries: z.array(z.string()),
  cities: z.array(z.string()).optional().default([]),
  social: z.string().optional().nullable(),
  airline: z.union([z.array(z.string()), z.string()]).optional().nullable(),
  tags: z.array(z.string()).optional().nullable(),
  main_image: z.string().optional().nullable(),
  main_image_crop: z.enum(['center', 'top', 'top_center', 'bottom_center', 'bottom']).optional().default('center'),
  publish: z.boolean().optional().default(true),
});

// English posts (source of truth)
const trips = defineCollection({
  loader: glob({ 
    pattern: '**/*.md', 
    base: '../travel_atlas/travel_archive' 
  }),
  schema: tripSchema,
});

// Spanish translations
const trips_es = defineCollection({
  loader: glob({ 
    pattern: '**/*.md', 
    base: '../travel_atlas/travel_archive_es' 
  }),
  schema: tripSchema,
});

export const collections = { trips, trips_es };

