# ScholarFinder 🎓

**Your Complete Guide to Studying Abroad**

A modern, responsive single-page web application with 151 scholarships, 86 universities, and 62 opportunities — all searchable and filterable.

## Features

- 🎯 **Scholarship Search** — Filter by level, field, country with instant results
- 🏫 **University Search** — Filter by ranking tier, tuition level, field, country
- 🚀 **Opportunities** — Internships, research, competitions, fellowships, summer schools, exchanges
- 💰 **Cost of Living** — Visual cost breakdowns for 51 cities + side-by-side comparison
- 🛂 **Visa Guide** — Requirements, documents, processing times for 26 countries
- 📝 **Test Prep** — IELTS, TOEFL, SAT, GRE, Duolingo with tips and resources
- ✍️ **Essay Help** — Personal statement, SOP, CV templates and guides
- ❓ **FAQ** — 42 searchable, accordion-style answers

## Tech Stack

- Pure HTML, CSS, JavaScript (no frameworks, no dependencies)
- Dark theme with blue/purple gradient accents
- Mobile-first responsive design
- CSS Grid + Flexbox layout
- JSON data loaded via fetch()

## Hosting

This is a static site ready for **GitHub Pages**:

1. Push this folder to a GitHub repository
2. Go to Settings → Pages → Deploy from main branch
3. Your site will be live at `https://yourusername.github.io/repo-name/`

## File Structure

```
website/
├── index.html          # Single page application
├── style.css           # All styles
├── script.js           # All JavaScript
├── README.md           # This file
└── data/
    ├── scholarships.json
    ├── universities.json
    ├── opportunities.json
    ├── cost_data.json
    ├── visa_data.json
    ├── faq_data.json
    ├── test_prep_data.json
    └── essay_guides.json
```

## Local Development

Simply open `index.html` in a browser, or serve with any static server:

```bash
# Python
python3 -m http.server 8000

# Node.js
npx serve .
```

> **Note:** Due to CORS, JSON files won't load via `file://`. Use a local server.

---

**Built by Scott Antwi**
**© 2026 Alpha Global Minds 🌍**
