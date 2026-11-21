
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(
            "https://www.saucedemo.com/",
            wait_until="domcontentloaded",
        )

        await page.locator('[data-test="username"]').fill("standard_user")
        await page.locator('[data-test="password"]').fill("secret_sauce")
        await page.locator('[data-test="login-button"]').click()

        await page.wait_for_url("**/inventory.html")

        await page.goto(
            "https://www.saucedemo.com/dynamic-catalog-lazy-load.html",
            wait_until="domcontentloaded",
        )

        cards = page.locator(".dynamic_catalog_card")

        for step in range(25):
            await page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )
            await page.wait_for_timeout(1500)

            loaded = await page.locator(
                ".dynamic_catalog_card_name"
            ).count()

            total = await cards.count()

            print(
                f"Шаг {step + 1}: "
                f"загружено товаров: {loaded}, "
                f"карточек: {total}"
            )

        print("\nНазвания загруженных товаров:")

        names = await page.locator(
            ".dynamic_catalog_card_name"
        ).all_text_contents()

        for name in names:
            print("-", name.strip())

        await browser.close()


asyncio.run(main())
