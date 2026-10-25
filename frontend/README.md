# Frontend

React 18 and Vite 5, styled with Tailwind CSS 3 through PostCSS and Autoprefixer.
Tailwind 3 is retained to match the project's existing dependency and Vite setup.

```sh
npm install
npm run dev
npm run build
npm run lint
```

The API URL is read from `VITE_API_URL`, defaulting to `http://localhost:8000`.

## Styling

- `tailwind.config.js`: scanned source paths and the shared teal `brand` palette.
- `src/index.css`: Tailwind layers, typography, form controls, focus styles,
  shared feedback states, and reduced-motion support.
- `src/App.css`: responsive application shell and navigation.
- `src/components/*.css`: component styles expressed with Tailwind `@apply`,
  kept alongside the existing components. These files use regular CSS rules
  because Vite processes each imported stylesheet independently.

Navigation runs horizontally on mobile and tablet, and vertically on desktop.
Forms and cards collapse to single-column layouts on small screens. Tables scroll
within their containers. Existing tabs remain mounted to retain their local state.

ESLint checks React code and accessibility rules. There is no frontend test script;
browser interaction checks require a running backend or mocked API responses.
