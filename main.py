import os
import sys
import time
import requests
import click
import configparser
import img2pdf
import tempfile
import atexit
import re
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt
from playwright.sync_api import sync_playwright

console = Console()

def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    defaults = {
        'quality': 2048,
        'scroll_delay': 1.0,
        'scroll_iterations': 10,
        'output': None
    }
    if 'SETTINGS' in config:
        settings = config['SETTINGS']
        defaults['quality'] = settings.getint('quality', 2048)
        defaults['scroll_delay'] = settings.getfloat('scroll_delay', 1.0)
        defaults['scroll_iterations'] = settings.getint('scroll_iterations', 10)
        defaults['output'] = settings.get('output', None) or None
    return defaults

def parse_page_selection(selection_str, total_pages):
    selection_str = selection_str.lower().strip()
    
    if selection_str == 'all' or not selection_str:
        return list(range(total_pages))
    
    selected_indices = set()
    
    try:
        parts = [p.strip() for p in selection_str.split(',')]
        
        for part in parts:
            if '-' in part:
                start, end = map(int, part.split('-'))
                if start < 1 or end > total_pages or start > end:
                    raise ValueError(f"Range {start}-{end} is out of document bounds (1-{total_pages}).")
                for i in range(start - 1, end):
                    selected_indices.add(i)
            else:
                p_num = int(part)
                if p_num < 1 or p_num > total_pages:
                    raise ValueError(f"Page number {p_num} is out of document bounds (1-{total_pages}).")
                selected_indices.add(p_num - 1)
        
        return sorted(list(selected_indices))
        
    except ValueError as e:
        if "out of document bounds" in str(e):
            raise e
        raise ValueError("Invalid format. Use 'all', a single number (e.g. 3), or range (e.g. 1-10).")

def log_history(url, title, pages_count, output_file):
    history_file = "history.json"
    history = []
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = []
            
    new_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": title,
        "url": url,
        "pages": pages_count,
        "output": output_file
    }
    
    history.append(new_entry)
    
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=4)

@click.command()
@click.argument('url', required=False)
@click.option('--output', '-o', help='Output filename')
@click.option('--pages', '-p', help='Page range (e.g. "all", "3", or "1-10")')
@click.option('--quality', '-q', type=int, help='Slide quality (2048 or 1024)')
@click.option('--delay', '-d', type=float, help='Delay between scrolls (seconds)')
@click.option('--quiet', is_flag=True, help='Disable progress output')
def main(url, output, pages, quality, delay, quiet):
    config_settings = load_config()
    
    if not url:
        url = Prompt.ask("[bold cyan]Input SlideShare URL[/bold cyan]")

    url = url.strip().strip("'\"")

    final_output = output if output is not None else config_settings['output']
    final_quality = quality if quality is not None else config_settings['quality']
    final_delay = delay if delay is not None else config_settings['scroll_delay']
    final_iterations = config_settings['scroll_iterations']

    if not quiet:
        console.print(f"\n[bold cyan]slidesharedl-py[/bold cyan] | [dim]Simple SlideShare Downloader[/dim]\n", justify="center")
    
    if "slideshare.net" not in url:
        console.print("[red]Error:[/red] Invalid SlideShare URL. Target mapping failed.")
        sys.exit(1)

    temp_dir_obj = tempfile.TemporaryDirectory(prefix="slidesharedl_")
    temp_dir = temp_dir_obj.name
    atexit.register(temp_dir_obj.cleanup)

    with sync_playwright() as p:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=quiet
        ) as progress:
            
            scan_task = progress.add_task("[cyan]Loading information from SlideShare...", total=None)
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1200, "height": 800})
            page = context.new_page()
            
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            from urllib.parse import unquote
            
            clean_url = url.split('#')[0].split('?')[0]
            url_slug = clean_url.rstrip('/').split('/')[-1]
            url_title = unquote(url_slug).replace('-', ' ').replace('_', ' ').title()
            
            doc_title = page.evaluate("""() => {
                const ogTitle = document.querySelector('meta[property="og:title"]')?.content;
                if (ogTitle && ogTitle.toLowerCase() !== 'slideshare') return ogTitle;
                const h1Title = document.querySelector('h1')?.innerText;
                return h1Title || "";
            }""")
            
            if not doc_title:
                doc_title = url_title or page.title().replace(' | SlideShare', '').strip()

            doc_title = re.sub(r'[<>:"/\\|?*]', '', doc_title).strip('. ')
            if not doc_title or doc_title.lower() == 'slideshare':
                 doc_title = "Archived_Presentation"

            if not quiet:
                console.print(f"[dim]Title:[/dim]          [bold white]{doc_title}[/bold white]")

            last_pos = 0
            for _ in range(60): 
                page.evaluate("window.scrollBy(0, 1200)")
                time.sleep(0.4)
                new_pos = page.evaluate("window.pageYOffset")
                if new_pos == last_pos: break
                last_pos = new_pos

            image_urls_raw = page.evaluate("""() => {
                const imgs = Array.from(document.querySelectorAll('img[class*="VerticalSlideImage"], img[data-full], .slide-image'));
                return imgs.map(img => img.getAttribute("data-full") || img.getAttribute("data-normal") || img.getAttribute("src"));
            }""")
            browser.close()

            filtered_urls = []
            seen = set()
            for u in image_urls_raw:
                if not u or not u.startswith("http") or u in seen: continue
                if "slidesharecdn.com" not in u and "sscdn.co" not in u: continue
                
                seen.add(u)
                clean_u = u.replace("-1024.jpg", f"-{final_quality}.jpg").replace("-2048.jpg", f"-{final_quality}.jpg").replace("-638.jpg", f"-{final_quality}.jpg").split("?")[0]
                filtered_urls.append(clean_u)
            
            if not filtered_urls:
                console.print("[red]Error:[/red] No slide assets detected. Source might be restricted.")
                sys.exit(1)

            num_slides = len(filtered_urls)
            if not quiet:
                console.print(f"[dim]Total Pages:[/dim]     [bold cyan]{num_slides}[/bold cyan]")

        selected_pages_str = pages
        if not selected_pages_str:
            selected_pages_str = Prompt.ask(
                "\n[bold yellow]Select Pages[/bold yellow] [dim](example: all, 5, or 1-10)[/dim]", 
                default="all"
            )
        
        try:
            page_indices = parse_page_selection(selected_pages_str, num_slides)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {str(e)}")
            sys.exit(1)
            
        selected_urls = [filtered_urls[i] for i in page_indices]
        num_selected = len(selected_urls)

        local_paths = [None] * num_selected
        def download_slide(idx, asset_url):
            local_path = os.path.join(temp_dir, f"slide_{idx+1:03d}.jpg")
            for attempt in range(3):
                try:
                    r = requests.get(asset_url, timeout=20)
                    if r.status_code == 200:
                        with open(local_path, "wb") as f: f.write(r.content)
                        return idx, local_path
                except requests.RequestException:
                    time.sleep(2)
            return idx, None

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
            disable=quiet
        ) as progress:
            dl_task = progress.add_task(f"[green]Downloading slides...", total=num_selected)

            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(download_slide, i, asset_url): i for i, asset_url in enumerate(selected_urls)}
                for future in as_completed(futures):
                    idx, path = future.result()
                    if path: local_paths[idx] = path
                    progress.advance(dl_task)

            final_paths = [p for p in local_paths if p is not None]

            if final_paths:
                pdf_task = progress.add_task("[yellow]Saving to PDF file...", total=100)
                output_file = final_output or f"{doc_title}.pdf"
                
                if not output_file.lower().endswith(".pdf"):
                    output_file += ".pdf"
                    
                if selected_pages_str.lower() != "all":
                    clean_range = selected_pages_str.replace(' ', '')
                    output_file = f"{os.path.splitext(output_file)[0]}_[{clean_range}].pdf"

                if not os.path.isabs(output_file) and not os.path.dirname(output_file):
                    os.makedirs("output", exist_ok=True)
                    output_file = os.path.join("output", output_file)

                with open(output_file, "wb") as f:
                    f.write(img2pdf.convert(final_paths))
                
                progress.update(pdf_task, completed=100)
                time.sleep(0.5)
                
                log_history(url, doc_title, len(page_indices), output_file)
                
                try:
                    temp_dir_obj.cleanup()
                    atexit.unregister(temp_dir_obj.cleanup)
                except Exception:
                    pass
                
                if not quiet:
                    console.print(f"\n[bold green]Success![/bold green] Saved as: [white]{output_file}[/white]")
            else:
                console.print("[red]Error:[/red] No slides captured. Downloading failed.")

if __name__ == "__main__":
    main()