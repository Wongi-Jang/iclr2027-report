// The published pages, in nav order. Adding a venue means a report file, an
// entry here, a main-<venue>.jsx and an HTML file in vite.config.js.
export const PAGES = [
  { venue: 'iclr', name: 'ICLR', href: 'index.html' },
  { venue: 'neurips', name: 'NeurIPS', href: 'neurips.html' },
]

export const navFor = (venue) =>
  PAGES.map((p) => ({ ...p, current: p.venue === venue }))
