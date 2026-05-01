import { defineCollection, z } from 'astro:content';

const entries = defineCollection({
  type: 'content',
  schema: z.object({
    date: z.string(),
    verse_ref: z.string(),
    verse_text: z.string(),
    translation: z.string(),
    themes: z.array(z.string()),
    news_summary: z.string(),
    sources: z.array(
      z.object({
        title: z.string(),
        url: z.string(),
        outlet: z.string(),
      })
    ),
  }),
});

export const collections = { entries };
