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

@click.command()
@click.argument('url', required=False)
@click.option('--output', '-o', help='Output filename')
@click.option('--quality', '-q', type=int, help='Slide quality (2048 or 1024)')
@click.option('--delay', '-d', type=float, help='Delay between scrolls (seconds)')
def main(url, output, quality, delay):
    config_settings = load_config()
    
    if not url:
        url = Prompt.ask("[bold cyan]Input SlideShare URL[/bold cyan]")

    final_output = output if output is not None else config_settings['output']
    final_quality = quality if quality is not None else config_settings['quality']
    final_delay = delay if delay is not None else config_settings['scroll_delay']
    final_iterations = config_settings['scroll_iterations']

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
            console=console
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
            console.print(f"[dim]Total Pages:[/dim]     [bold cyan]{num_slides}[/bold cyan]")

        local_paths = [None] * num_slides
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
            console=console
        ) as progress:
            dl_task = progress.add_task(f"[green]Downloading slides...", total=num_slides)

            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(download_slide, i, asset_url): i for i, asset_url in enumerate(filtered_urls)}
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

                if not os.path.isabs(output_file) and not os.path.dirname(output_file):
                    os.makedirs("output", exist_ok=True)
                    output_file = os.path.join("output", output_file)

                with open(output_file, "wb") as f:
                    f.write(img2pdf.convert(final_paths))
                
                progress.update(pdf_task, completed=100)
                time.sleep(0.5)
                
                try:
                    temp_dir_obj.cleanup()
                    atexit.unregister(temp_dir_obj.cleanup)
                except Exception:
                    pass
                
                console.print(f"\n[bold green]Success![/bold green] Saved as: [white]{output_file}[/white]")
            else:
                console.print("[red]Error:[/red] No slides captured. Downloading failed.")

if __name__ == "__main__":
    main()