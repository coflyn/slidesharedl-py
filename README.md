# slidesharedl-py 🎥

> Simple tool to save SlideShare presentations as PDF files.

![Version](https://img.shields.io/badge/version-2.0.0-cyan.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**slidesharedl-py** is a CLI tool to help you save SlideShare presentations into PDF format. It aims to capture slides at their highest available resolution and handles lazy-loading automatically.

---

### ⚠️ Legal Disclaimer

This tool is for personal archival of publicly available content or presentations you have permission to access. The developer is not responsible for any copyright infringements or misuse.

---

### Key Features

- **Smart Loading**: Automatically detects and loads every slide in the background.
- **Auto-Retry**: Tries again if a slide fails to download (up to 3 times).
- **High Quality**: Captures slides in HD (2048px) for better reading and printing.
- **Join PDF**: Combines all slides into a single, clean PDF file.

---

### Installation

1. **Clone & Setup Environment**

   ```bash
   git clone https://github.com/coflyn/slidesharedl-py.git
   cd slidesharedl-py
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

### Usage

Simply run the script with the presentation link:

```bash
python main.py "SLIDESHARE_URL"
```

**Custom Settings:**
All parameters can be tuned in `config.ini`. You can also override using flags:

- `-o, --output` : Custom name for the final PDF.
- `-q, --quality` : High res (2048) or Mid res (1024).

**Example:**

```bash
python main.py "https://www.slideshare.net/..." --quality 1024
```

---

### Supported Contents

- [x] SlideShare Presentations

---

### 📄 License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.
