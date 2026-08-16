# SlideShare Downloader (slidesharedl-py) 📄

> Simple tool to save SlideShare presentations as PDF, PPTX, or DOCX files.

![Version](https://img.shields.io/badge/version-3.1.0-cyan.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**SlideShare Downloader (slidesharedl-py)** is a CLI tool that helps you save SlideShare presentations into PDF, PPTX (PowerPoint), or DOCX (Word) files for offline reading and presentation. It captures slides at their highest available resolution (HD 2048px) and handles lazy-loading automatically.

---

### ⚠️ Legal Disclaimer

This tool is intended for personal archival of presentations you already have legal access to. Please respect SlideShare's Terms of Service and the intellectual property of the authors. The developers are not responsible for any misuse of this tool.

---

### Key Features

- **Multi-Format Export**: Save presentations as **PDF**, **PPTX** (PowerPoint), or **DOCX** (Word Document).
- **Smart Loading**: Automatically detects and loads every slide asset in the background.
- **Auto-Organized Output**: Downloaded files are neatly saved into the `output/` folder by default.
- **Safe Naming**: Automatically sanitizes filenames so they work flawlessly across Windows, Mac, and Linux.
- **Reliable Cleanup**: Temporary files are handled safely and automatically cleaned up, even if you stop the script midway.
- **High Quality**: Captures slides in HD (2048px) for better reading and printing.
- **Pick Pages**: Download the whole presentation or just specific pages (e.g., `1-10`).
- **Parallel Downloading**: Downloads slides concurrently using multi-threading for maximum speed.
- **History Log**: Keeps a record of each download in `history.json`.

---

### Installation

1. **Clone & Setup Environment**

   ```bash
   git clone https://github.com/coflyn/slidesharedl-py.git
   cd slidesharedl-py
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Requirements**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

---

### Usage

Simply run the script with the presentation link:

```bash
python main.py <enter>
# or
python main.py "SLIDESHARE_URL"
```

**CLI Options:**

- `-f, --format` : Export format (`pdf`, `pptx`, or `docx`). Default: `pdf`.
- `-o, --output` : Custom output filename.
- `-p, --pages` : Page selection (`all`, `3`, or `1-10`).
- `-q, --quality`: Slide resolution (`2048` for HD or `1024` for SD).
- `-d, --delay` : Custom delay per scroll step (seconds).
- `--quiet` : Disable progress output (silent mode).

**Examples:**

```bash
# Export as PowerPoint PPTX
python main.py "https://www.slideshare.net/slideshow/.../..." --format pptx

# Export as Word Document DOCX
python main.py "https://www.slideshare.net/slideshow/.../..." --format docx --pages "1-5"
```

---

### ⚙️ Configuration (`config.ini`)

You can set permanent default options in `config.ini` so you don't need to specify CLI flags every time:

```ini
[SETTINGS]
# Desired slide quality in pixels (2048 for HD or 1024 for SD)
quality = 2048

# Default export format (pdf, pptx, or docx)
format = pdf

# Pause duration during scrolling in seconds (default: 1.0)
scroll_delay = 1.0

# Number of scroll iterations to trigger lazy loading
scroll_iterations = 5

# Default output filename (Leave empty to auto-detect presentation title)
output =
```

---

### Supported Contents

- [x] SlideShare Presentations

---

### 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to check the [issues page](https://github.com/coflyn/slidesharedl-py/issues) if you want to contribute.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Don't forget to give a ⭐ if you find this project useful!

---

### 🐛 Issue Reporting & Support

Found a bug, broken link extraction, or script error?
Please feel free to open an issue with the error traceback and the target URL:

👉 **[Open an Issue on GitHub](https://github.com/coflyn/slidesharedl-py/issues)**

---

### 📄 License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.
