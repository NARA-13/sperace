"""Capture a screen sequence of the running web build with mouse steering."""
import asyncio, sys
from playwright.async_api import async_playwright

URL = "http://127.0.0.1:8099/index.html"
OUT = "/home/user/.cache/build/gallery"


async def run_race(pg, mode_y, tag, seconds=26):
    await pg.mouse.click(640, 300)
    await pg.wait_for_timeout(250)
    await pg.mouse.move(1175, mode_y)
    await pg.mouse.down(); await pg.wait_for_timeout(70); await pg.mouse.up()
    await pg.wait_for_timeout(4200)          # countdown
    await pg.keyboard.down("w")
    shots = [8, 16, 24]
    t0 = 0
    for i, s in enumerate(shots):
        while t0 < s:
            await pg.wait_for_timeout(1000)
            t0 += 1
        await pg.screenshot(path=f"{OUT}/{tag}_{i}.png")
    await pg.keyboard.up("w")


async def main():
    import os
    os.makedirs(OUT, exist_ok=True)
    logs = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=[
            "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
            "--no-sandbox", "--autoplay-policy=no-user-gesture-required"])
        pg = await b.new_page(viewport={"width": 1280, "height": 720})
        pg.on("console", lambda m: logs.append(f"[{m.type}] {m.text}"))
        pg.on("pageerror", lambda e: logs.append(f"[pageerror] {e}"))
        await pg.goto(URL)
        await pg.wait_for_timeout(8000)
        await pg.screenshot(path=f"{OUT}/00_menu.png")
        await run_race(pg, 187, "01_classic")
        await b.close()
    print("\n".join(l for l in logs if "error" in l.lower())[:2000])


asyncio.run(main())
