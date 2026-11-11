"""Universal Gamma Vendoring: download everything, patch CDN, auto-stub missing."""
import asyncio
from playwright.async_api import async_playwright
import pathlib, os, re, urllib.parse

TARGET_URL = os.environ.get("TARGET_URL", "https://iskusstvo-zaboty-o-t-qqkkaff.gamma.site/")
ROOT = pathlib.Path(".")

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        c = await b.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        
        async def handle_route(route):
            url = route.request.url
            if url.startswith("data:") or url.startswith("blob:"):
                return await route.continue_()
            try:
                response = await route.fetch()
                body = await response.body()
                if response.ok and url.startswith("http"):
                    parsed = urllib.parse.urlparse(url)
                    path = parsed.path.lstrip("/")
                    if path.startswith("5s9bbrdpq/"): path = path[len("5s9bbrdpq/"):]
                    if not path: path = "index.html"
                    filepath = ROOT / path
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    if not filepath.exists():
                        with open(filepath, "wb") as f:
                            f.write(body)
                await route.fulfill(response=response)
            except Exception:
                await route.continue_()

        await c.route("**/*", handle_route)
        page = await c.new_page()
        print(f"Navigating to {TARGET_URL}...")
        await page.goto(TARGET_URL, wait_until="networkidle", timeout=90000)

        # Скролл и клики для загрузки lazy-chunks
        for _ in range(10):
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(500)

        images = await page.query_selector_all("img")
        for img in images:
            try:
                await img.click(timeout=1000)
                await page.wait_for_timeout(300)
                await page.mouse.click(10, 10)
                await page.wait_for_timeout(300)
            except:
                pass

        await page.wait_for_timeout(5000)
        html = await page.content()
        await b.close()

    print("Patching HTML...")
    cdn_regex = re.compile(r'https?://assets\.gammahosted\.com(?:/[a-z0-9]+)?')
    html_str = cdn_regex.sub('', html)
    html_str = html_str.replace("url('/**/')", "none").replace('url("/**/")', "none")
    
    pathlib.Path("index.html").write_text(html_str, encoding="utf-8")

    patched_count = 0
    for filepath in ROOT.rglob("*"):
        if filepath.is_file() and filepath.suffix in [".js", ".css", ".json"]:
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                if "gammahosted.com" in content:
                    content = cdn_regex.sub('', content)
                    filepath.write_text(content, encoding="utf-8")
                    patched_count += 1
            except Exception:
                pass

    # === АВТО-ЗАГЛУШКИ ===
    print("Creating stubs for missing chunks...")
    html = pathlib.Path("index.html").read_text(encoding="utf-8")
    referenced = set(re.findall(r'/_next/static/immutable/chunks/([a-zA-Z0-9_-]+\.js)', html))
    stubs_created = 0
    for chunk in referenced:
        filepath = ROOT / "_next" / "static" / "immutable" / "chunks" / chunk
        if not filepath.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text("// stub for offline mode", encoding="utf-8")
            stubs_created += 1

    print(f"✅ Done. Patched {patched_count} files. Created {stubs_created} stubs.")

if __name__ == "__main__":
    asyncio.run(main())
