import asyncio
import subprocess
from typing import Optional

import netron
import playwright
from playwright.async_api import async_playwright


async def save_model_graphs(netron_url: str, out_path: Optional[str], timeout: int):
    """
    Opens the netron app in a fake browser and executes the export to png or svg.

    Args:
        netron_url (str): URL of the Netron server.
        out_path (str): Path of the output file (either *.png or *.svg).
        timeout (int): Timeout of requests in ms.
    """

    try:  # Big try/catch block so that we can properly terminate the function (otherwise the script never finishes)
        async with async_playwright() as pw:
            try:
                browser = await pw.chromium.launch()
            except playwright._impl._api_types.Error as browser_error:
                # This probably means that the browser extension has not been installed, so we try to run the command
                print(str(browser_error))
                print("Will install playwright-chromium and try again...")
                subprocess.run(["playwright", "install", "chromium"], check=True)
                browser = await pw.chromium.launch()

            page = await browser.new_page()
            await page.goto(netron_url)

            # Click on the main button Accept of the first screen
            await page.click("#message-button", timeout=timeout)
            # Wait for the main page to load (= body class turns to 'default')
            await page.wait_for_selector("body.default", timeout=timeout)

            async def click_and_download(button_id: str, out_file: str):
                """
                Helper function to simulate the click on a button and write the downloaded file to a target location.
                """

                assert button_id

                # Click on the hamburger button to show the menu
                await page.click("#menu-button", timeout=timeout)

                # Start waiting for the download (triggered by netron when we click on the "Export to SVG" button)
                async with page.expect_download() as download_info:
                    # Perform the action that initiates download, in this case click on the aforementioned button
                    await page.click(button_id, timeout=timeout)

                download = await download_info.value
                # Wait for the download process to complete
                print(await download.path())
                # Save downloaded file to target location
                await download.save_as(out_file)
                print(f"Saved model architecture to {out_file}")

            # Actually perform the downloads
            assert out_path
            if out_path.endswith(".png"):
                await click_and_download("#menu-item-0-1", out_path)  # save to PNG
            elif out_path.endswith(".svg"):
                await click_and_download("#menu-item-0-2", out_path)  # save to SVG
            else:
                raise ValueError("Output file must have .svg or .png extension")

            await browser.close()

    except Exception as err:
        print(f"Exception: {err}")
        asyncio.get_event_loop().stop()


def export_graph(model_path: str, output: str, port: str, timeout: int):
    """
    Provides the main functionality of `netron_export_graph`
    """
    try:
        HOST = "127.0.0.1"
        # Starts the netron server locally
        netron.start(file=model_path, address=(HOST, port), browse=False)
        # Run the main function
        asyncio.run(
            save_model_graphs(netron_url=f"http://{HOST}:{port}", out_path=output, timeout=timeout))
    finally:
        # Stops the netron server
        netron.stop()
