# ♨️ OKOnsen - Japan Hot Spring & Ryokan Discovery Map

An interactive, multi-language web platform designed to help global travelers discover their perfect Japanese Onsen and Ryokan. Filter locations by specific needs (Tattoo-friendly, Private Baths, Luxury) and explore deeply detailed, SEO-optimized guides.

🔗 **Live Demo:** https://okonsen.net

---

## ✨ Key Features

* **Interactive Map UI**: Explore curated hot springs across Japan using a custom Google Maps interface with interactive markers.
* **Niche Theme Filtering**: Instantly filter onsens by highly sought-after themes:
  * 🛁 Private Bath (Kashikiri-buro)
  * ⭕ Tattoo OK
  * 🗻 Great View (Mt. Fuji, Ocean, Mountains)
  * ✨ Luxury Ryokan
  * 🏮 Local / Hidden Gems
* **Native Multi-Language Support**: Seamlessly switch between **English** and **Korean** content without relying on widget translators.
* **AI-Powered Mega Content**: Automated content generation using **Google Gemini 2.5 Flash**, producing 7,000+ character SEO-optimized articles with Midjourney image prompts.
* **Affiliate Monetization Ready**: Deep link integration for Agoda to maximize booking conversions.
* **Ultra-Fast Performance**: No traditional databases. Markdown files are compiled into a lightweight JSON file and cached in memory using Flask.

---

## 🛠️ Tech Stack & Architecture

* **Backend**: Python 3.10, Flask (with `flask-compress` and Gunicorn)
* **Frontend**: Vanilla JavaScript (ESM), HTML5, CSS3, Google Maps API (Advanced Markers)
* **Data & Content**: Markdown with YAML Frontmatter compiled to JSON
* **AI Integration**: `google-genai` (Gemini 2.5 Flash API)
* **Image Processing**: Pillow (PIL) for automated resizing and compression
* **Infrastructure**: Docker, Google Cloud Run, Cloud Build

---

## 🤖 Powerful Automation Scripts

This project includes highly efficient Python scripts to automate content creation and optimize assets.

### 1. `script/onsen_generator.py`
Reads `script/csv/onsens.csv` and automatically generates bilingual (EN/KO) Markdown files.
* Generates 7k-8k character deep-dive articles (History, Water Quality, Kaiseki, Access).
* Automatically creates Midjourney prompts for fake/conceptual imagery.
* Handles API rate limits safely (`time.sleep`).

### 2. `script/optimize_images.py`
Scans the `app/static/images/` directory to compress heavy images.
* Resizes images to max 800px width.
* Converts formats to lightweight `.jpg` (quality: 75%).
* Protects essential UI assets (e.g., `logo.png`, `favicons.ico`).

### 3. `script/build_data.py`
Compiles all `.md` files in `app/content/` into a single `onsen_data.json` for the frontend.
* Auto-generates `sitemap.xml` for SEO.

---

## 🚀 How to Run Locally

### 1. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/starful/okonsen.git
cd okonsen
pip install -r requirements.txt
```

### 2. Set Up Environment Variables
Create a `.env` file in the root directory and add your Gemini API key:
```env
GEMINI_API_KEY=your_google_gemini_api_key_here
```

### 3. Generate & Build Data
```bash
# 1. Optimize downloaded images
python script/optimize_images.py

# 2. Generate Markdown files via AI (Reads onsens.csv)
python script/onsen_generator.py

# 3. Build JSON data and Sitemap
python script/build_data.py
```

### 4. Run the Server
```bash
python app/__init__.py
# or using gunicorn:
# gunicorn --bind 0.0.0.0:8080 app:app
```
Visit `http://localhost:8080` in your browser.

---

## 📂 Project Structure

```text
okonsen/
├── app/
│   ├── content/                 # Generated Markdown files
│   ├── static/                  # CSS, JS, Images, JSON
│   ├── templates/               # HTML Templates
│   └── __init__.py              # Flask App Entry
├── script/
│   ├── csv/
│   │   └── onsens.csv           # Master list of Onsens & Agoda Links
│   ├── build_data.py            # MD to JSON/XML compiler
│   ├── onsen_generator.py       # Gemini AI Content Bot
│   └── optimize_images.py       # Image Compressor
├── .env                         # API Keys (Git Ignored)
├── Dockerfile                   
├── cloudbuild.yaml              
└── requirements.txt             
```

---

## 🛡️ License

This project is proprietary and maintained by the OKOnsen Project Team.
