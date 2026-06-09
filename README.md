# Threads Affiliate Intelligence System

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Production-orange.svg)

Sistem otomatisasi affiliate marketing berbasis AI untuk platform Threads. Sistem ini secara otomatis mencari postingan yang relevan, menganalisis niat beli pengguna, mencocokkan dengan produk Shopee, dan menghasilkan balasan affiliate yang siap dipublikasikan.

---

## Description

Threads Affiliate Intelligence System adalah aplikasi automation yang dirancang untuk membantu affiliate marketer menjalankan kampanye Shopee Affiliate di platform Threads dengan lebih efisien. Sistem ini menggunakan Google Gemini AI untuk:

- **Mendeteksi** postingan pengguna yang memiliki niat beli
- **Menganalisis** kategori produk yang dibutuhkan
- **Mencocokkan** dengan produk Shopee yang relevan
- **Menghasilkan** link affiliate dan draft balasan secara otomatis

Alur kerja fully automated dengan human-in-the-loop approval melalui dashboard admin.

---

## Features

### Core Features

| Feature | Description |
|---------|-------------|
| **Threads Monitoring** | Scraping postingan Threads berdasarkan keyword dengan auto-scroll dan lazy-loading handling |
| **AI Intent Scoring** | Analisis niat beli menggunakan Gemini AI dengan skor 0-100 |
| **AI Category Detection** | Klasifikasi produk ke dalam 6 kategori: Fashion, Beauty, Gaming, Electronics, Home, Health |
| **Shopee Product Search** | Pencarian produk di Shopee Affiliate menggunakan Playwright automation |
| **AI Product Matching** | Pencocokan produk dengan konteks postingan menggunakan Gemini AI |
| **Affiliate Link Generation** | Konversi URL produk ke link affiliate (shp.ee) via Shopee Affiliate Dashboard |
| **AI Reply Generation** | Generate draft balasan natural dan soft-selling dalam Bahasa Indonesia |
| **Dashboard Admin** | Web UI untuk review, approve, edit, atau skip draft balasan |
| **Auto-Poster** | Posting balasan yang sudah di-approve ke Threads |
| **Analytics** | Statistik performa berdasarkan status, kategori, dan intent score |

### Technical Features

- **Retry Mechanism** dengan exponential backoff untuk API calls
- **Request Timeout** 30 detik untuk mencegah infinite hang
- **Resource Cleanup** otomatis untuk browser Playwright
- **Enhanced Logging** dengan stack trace untuk debugging
- **SQLite Database** dengan SQLAlchemy ORM (support PostgreSQL)
- **CSRF Protection** pada dashboard admin
- **Session Persistence** untuk login Threads dan Shopee

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        THREADS AFFILIATE PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
  │   Threads    │────▶│ AI Intent    │────▶│ AI Category  │────▶│  Shopee  │
  │   Monitor    │     │   Scorer     │     │  Detector    │     │  Search  │
  │  (Scraping)  │     │  (Gemini)    │     │  (Gemini)    │     │  Finder  │
  └──────────────┘     └──────────────┘     └──────────────┘     └──────────┘
                                                                          │
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐              │
  │  Dashboard   │◀────│   Reply      │◀────│   Product    │◀─────────────┘
  │   Admin      │     │  Generator   │     │   Matcher    │
  │  (Approve)   │     │  (Gemini)    │     │  (Gemini)    │
  └──────────────┘     └──────────────┘     └──────────────┘
         │
         │ (Approved posts)
         ▼
  ┌──────────────┐     ┌──────────────┐
  │  Auto-Poster │────▶│   Threads    │
  │              │     │   (Reply)    │
  └──────────────┘     └──────────────┘
```

### Pipeline Flow

1. **Scrape**: `ThreadsMonitor` mencari dan scrape postingan berdasarkan keyword
2. **Score**: `AIIntentScorer` memberikan skor intent (0-100), post dengan skor < 70 di-skip
3. **Detect**: `AICategoryDetector` mendeteksi kategori produk
4. **Search**: `ShopeeProductFinder` mencari produk di Shopee
5. **Match**: `AIProductMatcher` mencocokkan produk terbaik dengan postingan
6. **Link**: `ShopeeLinkGenerator` menghasilkan link affiliate
7. **Draft**: `AIReplyGenerator` generate draft balasan
8. **Review**: Dashboard admin untuk approve/edit/skip
9. **Post**: `ThreadsPoster` mengirim balasan yang sudah approve

---

## Project Structure

```
Threads/
├── main.py                    # Entry point CLI
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
│
├── core/                      # Core configuration
│   ├── config.py              # Config class dengan environment variables
│   └── logger.py              # Logging setup utility
│
├── database/                  # Database layer
│   ├── db.py                  # SQLAlchemy engine & session factory
│   ├── models.py              # ORM models (ThreadPost, SystemLog, AffiliateLink, ProductMetric)
│   └── repositories/          # Data access layer
│       ├── post_repository.py
│       └── log_repository.py
│
├── modules/                   # Business logic modules
│   ├── threads/               # Threads platform integration
│   │   ├── session.py         # Login & session management
│   │   ├── monitor.py         # Post scraping
│   │   └── poster.py          # Auto-posting
│   │
│   ├── shopee/                # Shopee platform integration
│   │   ├── session.py         # Shopee affiliate login
│   │   ├── product_finder.py  # Product search automation
│   │   └── link_generator.py  # Affiliate link generation
│   │
│   ├── ai/                    # AI modules (Gemini)
│   │   ├── intent_scorer.py   # Intent analysis
│   │   └── category_detector.py # Category detection
│   │
│   ├── matcher/               # AI matching modules
│   │   ├── product_matcher.py # Product-to-post matching
│   │   ├── reply_generator.py # Reply draft generation
│   │   └── ranking_engine.py  # Product scoring
│   │
│   └── dashboard/             # Flask web dashboard
│       ├── app.py             # Flask application
│       └── templates/         # HTML templates
│           ├── index.html     # Post list
│           ├── detail.html    # Post detail & actions
│           └── analytics.html # Statistics
│
└── sessions/                  # Browser session files (runtime)
    ├── threads_session.json   # Threads login session
    └── shopee_session.json    # Shopee login session
```

---

## Requirements

### Software

- **Python**: 3.9 atau lebih tinggi
- **Chromium Browser**: Untuk Playwright automation
- **Database**: SQLite (default) atau PostgreSQL

### Python Dependencies

```
Flask>=3.0.0
playwright>=1.40.0
google-generativeai>=0.4.0,<1.0.0
python-dotenv>=1.0.0
SQLAlchemy>=2.0.0
flask-wtf>=1.2.0
```

---

## Installation

### Prerequisites

```bash
# Install Python 3.9+ (Ubuntu)
sudo apt update
sudo apt install python3.9 python3.9-venv python3-pip

# Install Chromium dependencies (Ubuntu)
sudo apt install -y wget gnupg ca-certificates procps libnspr4 libnss3 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2
```

### Step 1: Clone Repository

```bash
git clone https://github.com/Agelakz/Threads.git
cd Threads
```

### Step 2: Create Virtual Environment

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install Playwright Browsers

```bash
playwright install chromium
playwright install-deps chromium
```

### Step 5: Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit with your credentials
nano .env
```

### Step 6: Setup Login Sessions

```bash
# Login ke Threads (diperlukan manual untuk pertama kali - ada OTP/Captcha)
python -c "from modules.threads.session import ThreadsSessionManager; ThreadsSessionManager().login(headless=False)"

# Login ke Shopee Affiliate (diperlukan manual untuk pertama kali)
python -c "from modules.shopee.session import ShopeeSessionManager; ShopeeSessionManager().login(headless=False)"
```

---

## Environment Variables

Buat file `.env` di root directory dengan konfigurasi berikut:

```env
# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Threads Configuration
THREADS_USERNAME=your_threads_username
THREADS_PASSWORD=your_threads_password

# Shopee Affiliate Configuration
SHOPEE_AFFILIATE_USERNAME=your_shopee_username
SHOPEE_AFFILIATE_PASSWORD=your_shopee_password

# Database Configuration (SQLite default)
DATABASE_URL=sqlite:///database.db

# Flask Configuration
FLASK_APP=main.py
FLASK_ENV=development
FLASK_SECRET_KEY=generate_a_random_secret_key_here
```

### Getting Gemini API Key

1. Kunjungi [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Buat API key baru
3. Salin ke `GEMINI_API_KEY`

---

## Usage

### Dashboard Admin

Jalankan dashboard web untuk review dan approve draft balasan:

```bash
python main.py --dashboard
```

Dashboard tersedia di `http://localhost:5000`

**Fitur Dashboard:**
- `/` - Daftar semua post dengan filter status
- `/post/<id>` - Detail post dengan form approve/edit/skip
- `/analytics` - Statistik dan metrik performa

### Pipeline Utama

Jalankan pipeline untuk scrape, analisis, dan generate draft:

```bash
# Basic usage
python main.py --keyword "rekomendasi skincare"

# Dengan limit
python main.py --keyword "laptop gaming" --limit 10

# Dengan browser visible (untuk debugging)
python main.py --keyword "sepatu running" --visible
```

### Auto-Poster

Kirim balasan yang sudah di-approve ke Threads:

```bash
# Post approved replies
python main.py --post

# Dengan browser visible
python main.py --post --visible
```

### CLI Help

```bash
python main.py --help
```

Output:
```
usage: main.py [-h] [--keyword KEYWORD] [--limit LIMIT] [--visible] [--dashboard] [--post]

Threads Affiliate Intelligence System

options:
  --keyword KEYWORD    Keyword yang dicari di Threads
  --limit LIMIT        Jumlah maksimal post yang di-scrape (default: 5)
  --visible            Jalankan browser tanpa mode headless
  --dashboard          Jalankan web dashboard
  --post               Jalankan auto-poster
```

---

## Workflow

### Complete Workflow

```
1. INITIAL SETUP (Sekali saja)
   ├── Install dependencies
   ├── Setup environment variables
   ├── Login Threads session
   └── Login Shopee session

2. DAILY PIPELINE
   ├── Run pipeline dengan keyword
   │   └── python main.py --keyword "rekomendasi skincare" --limit 10
   │
   ├── Sistem akan:
   │   ├── Scrape postingan Threads
   │   ├── Analyze intent dengan AI
   │   ├── Detect category
   │   ├── Search produk di Shopee
   │   ├── Match produk terbaik
   │   ├── Generate affiliate link
   │   └── Generate reply draft
   │
   └── Post tersimpan di database dengan status ANALYZED

3. REVIEW & APPROVE
   ├── Buka dashboard: python main.py --dashboard
   ├── Review setiap post dan draft
   ├── Approve / Edit / Skip
   └── Status berubah ke APPROVED

4. AUTO-POST
   ├── Jalankan poster: python main.py --post
   └── Sistem posting balasan ke Threads
```

### Status Flow

```
PENDING → ANALYZED → APPROVED → SENT
    │          │          │
    │          │          └── Reply berhasil terkirim
    │          │
    │          └── Draft balasan siap di-review
    │
    └── Post baru, belum diproses
```

### Post Statuses

| Status | Description |
|--------|-------------|
| `PENDING` | Post baru, belum diproses pipeline |
| `ANALYZED` | Sudah diproses, draft siap di-review |
| `APPROVED` | Draft disetujui admin |
| `SKIPPED` | Dilewati admin atau intent score < 70 |
| `SENT` | Reply berhasil terkirim ke Threads |
| `FAILED` | Gagal mengirim reply |

---

## Deployment

### VPS Ubuntu 22.04 Deployment

#### 1. Server Setup

```bash
# SSH ke server
ssh user@your-server-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.9 python3.9-venv python3-pip git nginx

# Install Chromium dependencies
sudo apt install -y wget gnupg ca-certificates procps libnspr4 libnss3 libdbus-1-3 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2
```

#### 2. Deploy Application

```bash
# Clone repository
git clone https://github.com/Agelakz/Threads.git
cd Threads

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Playwright
playwright install chromium
playwright install-deps chromium

# Setup environment
cp .env.example .env
nano .env  # Edit dengan credentials asli

# Setup sessions
python -c "from modules.threads.session import ThreadsSessionManager; ThreadsSessionManager().login(headless=False)"
python -c "from modules.shopee.session import ShopeeSessionManager; ShopeeSessionManager().login(headless=False)"
```

#### 3. PM2 Process Manager

```bash
# Install PM2
npm install -g pm2

# Start dashboard
pm2 start "source venv/bin/activate && python main.py --dashboard" --name threads-dashboard

# Setup startup script
pm2 startup
pm2 save
```

#### 4. Nginx Reverse Proxy (Optional)

```nginx
# /etc/nginx/sites-available/threads
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/threads /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 5. Cron Job untuk Pipeline

```bash
# Edit crontab
crontab -e

# Tambahkan (jalan setiap 6 jam)
0 */6 * * * cd /home/user/Threads && source venv/bin/activate && python main.py --keyword "rekomendasi skincare" --limit 20 >> /var/log/threads-pipeline.log 2>&1

# Tambahkan (auto-post setiap 30 menit)
*/30 * * * * cd /home/user/Threads && source venv/bin/activate && python main.py --post >> /var/log/threads-poster.log 2>&1
```

---

## Known Limitations

### Current Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **Session Expiration** | Threads/Shopee session perlu di-refresh manual | Setup scheduled task untuk re-login |
| **No Auto-Relogin** | Pipeline gagal jika session expired | Monitoring & manual re-login |
| **Single Keyword** | Pipeline berjalan per keyword | Run multiple times dengan keyword berbeda |
| **Browser Required** | Butuh Chromium untuk automation | Wajib install Playwright |
| **No Rate Limiting** | Bisa kena limit dari Gemini API | Implementasi throttle di masa depan |
| **SQLite Concurrency** | Tidak cocok untuk high-traffic | Migrate ke PostgreSQL untuk production |

### Deprecations

- `google-generativeai` package deprecated, migrate ke `google.genai` di masa depan

---

## Roadmap

### Planned Features

- [ ] **Auto Session Refresh** - Automatic re-login saat session expired
- [ ] **Multi-Keyword Queue** - Run pipeline dengan multiple keywords
- [ ] **Rate Limiting** - Throttle API calls untuk avoid limits
- [ ] **PostgreSQL Support** - Database migration untuk production
- [ ] **Notification System** - Email/Telegram notification saat ada post baru
- [ ] **A/B Testing** - Test different reply templates
- [ ] **Analytics Dashboard** - Real-time metrics visualization
- [ ] **User Authentication** - Dashboard admin dengan login
- [ ] **API REST** - Expose API untuk integrations

### Future Improvements

- [ ] Migrate to `google.genai` package
- [ ] Add unit tests
- [ ] Docker containerization
- [ ] Kubernetes deployment manifests
- [ ] Enhanced error recovery
- [ ] Circuit breaker pattern untuk external APIs

---

## License

MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Support

Untuk bantuan dan pertanyaan:
- Buat Issue di GitHub
- Hubungi maintainer

---

*Made with ❤️ for the Threads Affiliate Community*