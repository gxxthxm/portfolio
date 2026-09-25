# Gauthem Krishna — Portfolio

Personal portfolio of Gauthem Krishna, Product & UX Designer. A static rebuild of
[gauthemk.framer.website](https://gauthemk.framer.website/) with the same content,
dark design and URL structure — no Framer, no framework, no build dependencies.

## Structure

```
content/
  site.json              # name, links, intro, experience, tech stack, services, project order
  projects/<slug>.json   # one file per case study (title, category, cover, body blocks)
assets/
  css/style.css          # all styles (design tokens at the top)
  js/main.js             # mobile menu + scroll reveal
  images/                # all project images, self-hosted
build.py                 # generates the HTML pages from content/
index.html, about/, service/, contact/, professional_works/, other_works/   # generated
```

## Editing

1. Edit text in `content/site.json` or a project in `content/projects/`.
2. Rebuild the pages (Python 3, standard library only):

   ```bash
   python3 build.py
   ```

3. Commit the regenerated HTML along with your content changes.

To add a project, create `content/projects/<slug>.json` (copy an existing one),
put its images in `assets/images/`, and add the slug to `home`, `professional`
or `other` in `content/site.json`.

## Preview locally

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000.

## Deploy

The generated pages live at the repo root, so GitHub Pages can serve the `main`
branch directly: **Settings → Pages → Deploy from a branch → `main` / `(root)`**.
All links are relative, so it works at `https://<user>.github.io/portfolio/` or on a
custom domain.
