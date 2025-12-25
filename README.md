# ⛩️ JinjaMap - Japan Shrine Guide

**JinjaMap** is a web application that helps travelers discover hidden shrines and **"Power Spots"** across Japan. Whether you're looking for luck in **Wealth, Love, or Success**, JinjaMap guides you to the right spiritual destination.

🔗 **Live Demo:** [https://jinjamap.com](https://jinjamap.com)

---

## ✨ Features

*   **Interactive Map**: Visualize shrine locations with Google Maps integration.
*   **Theme Filtering**: Find shrines based on specific wishes:
    *   💰 **Wealth** (Money luck)
    *   ❤️ **Love** (Matchmaking)
    *   🎓 **Study** (Academic success)
    *   🛡️ **Safety** (Protection)
*   **Static Data Build**: Fast performance using pre-built JSON data from Markdown files.
*   **Omikuji (Fortune Slip)**: A fun mini-game to draw your daily fortune.
*   **Responsive Design**: Optimized for both desktop and mobile devices.

---

## 🛠️ Tech Stack

*   **Backend**: Python 3.10, Flask
*   **Frontend**: HTML5, CSS3, Vanilla JavaScript
*   **Data**: Markdown (`.md`) based content management
*   **Infrastructure**: Docker, Google Cloud Run
*   **CI/CD**: Google Cloud Build

---

## 📂 Project Structure

```text
jinjaMap/
├── app/
│   ├── content/            # Shrine data (Markdown files)
│   ├── static/             # Assets (CSS, JS, Images, JSON)
│   ├── templates/          # HTML Templates
│   └── __init__.py         # Flask Application Factory
│
├── script/                 # Helper scripts (Content Generator)
├── build_data.py           # Build Script (Markdown -> JSON)
├── Dockerfile              # Docker Configuration
├── cloudbuild.yaml         # CI/CD Configuration
└── requirements.txt        # Python Dependencies
```

---

## 🚀 How to Add New Content

You don't need a database. Just add a Markdown file!

1.  Create a new file in `app/content/` (e.g., `meiji_jingu.md`).
2.  Add the required **Frontmatter**:

```yaml
---
layout: post
title: "Meiji Jingu Shrine"
date: 2025-12-25
categories: [History, Peace]
tags: [Tokyo, PowerSpot, Emperor]
thumbnail: /content/images/meiji_jingu.webp
lat: 35.6764
lng: 139.6993
address: "1-1 Yoyogikamizonocho, Shibuya City, Tokyo"
excerpt: "A brief summary for the card view..."
---

(Write the full description here using Markdown...)
```

3.  Deploy! The `build_data.py` script will automatically compile it into the app.

---

## 📦 Deployment

This project is deployed to **Google Cloud Run** using **Cloud Build**.

```bash
# Trigger build and deploy
gcloud builds submit
```

The build process includes:
1.   installing dependencies.
2.  Running `build_data.py` to generate `shrines_data.json` & `sitemap.xml`.
3.  Containerizing the app and pushing to Google Artifact Registry.
4.  Deploying the new revision to Cloud Run.

---

## 🛡️ License

This project is open-source and available under the [MIT License](LICENSE).