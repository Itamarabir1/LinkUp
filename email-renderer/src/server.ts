import express, { Request, Response } from 'express';
import * as React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { TEMPLATE_REGISTRY } from './emails/registry';

const app = express();
app.use(express.json());

app.get('/health', (_req: Request, res: Response) => {
  res.json({ status: 'ok', templates: Object.keys(TEMPLATE_REGISTRY) });
});

app.post('/render', (req: Request, res: Response) => {
  const { template, props = {} } = req.body as {
    template: string;
    props: Record<string, unknown>;
  };

  if (!template) {
    return res.status(400).json({ error: 'Missing required field: template' });
  }

  const Component = TEMPLATE_REGISTRY[template];
  if (!Component) {
    return res.status(404).json({
      error: `Template '${template}' not found`,
      available: Object.keys(TEMPLATE_REGISTRY),
    });
  }

  try {
    const element = React.createElement(Component, props);
    const html = `<!DOCTYPE html>\n${renderToStaticMarkup(element)}`;
    return res.json({ html });
  } catch (err) {
    console.error(`[email-renderer] Error rendering ${template}:`, err);
    return res.status(500).json({
      error: 'Render failed',
      detail: err instanceof Error ? err.message : String(err),
    });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`[email-renderer] Running on port ${PORT}`);
  console.log(`[email-renderer] Templates: ${Object.keys(TEMPLATE_REGISTRY).join(', ')}`);
});
