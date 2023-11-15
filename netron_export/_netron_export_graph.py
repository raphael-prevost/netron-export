import argparse
import asyncio
import random
import subprocess
import warnings
from typing import List

import netron
import playwright
from playwright.async_api import async_playwright


async def save_model_graphs(netron_url: str, out_paths: List[str], horizontal_mode: bool, timeout: int):
    """
    Opens the netron app in a fake browser and executes the export to png or svg.

    Args:
        netron_url (str): URL of the Netron server.
        out_paths (List[str]): Paths of the output files (either *.png or *.svg)
        horizontal_mode (bool): Show the graph horizontally rather than vertically.
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
                try:
                    subprocess.run(["playwright", "install", "--with-deps", "chromium"], check=True, timeout=60)
                    browser = await pw.chromium.launch()
                except subprocess.TimeoutExpired as err:
                    warnings.warn(
                        "Could not install playwright dependencies (maybe it is asking for sudo privileges). Please install it manually with the command 'sudo playwright install --with-deps chromium'."
                    )
                    return
                print("Installation of playwright dependencies finished")

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

                # Click on the Horizontal mode button if requested
                if horizontal_mode:
                    await page.click("#menu-item-2-3", timeout=timeout)
                    # Re-open the menu
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
            for out_path in out_paths:
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


def export_graph(model_path: str,
                 output: List[str],
                 horizontal_mode: bool,
                 port: int,
                 timeout: int,
                 allowed_port_trials: int = 100):
    """
    Provides the main functionality of `netron_export`
    """

    try:
        HOST = "127.0.0.1"
        # Starts the netron server locally
        netron.start(file=model_path, address=(HOST, port), browse=False)
        # Run the main function
        asyncio.run(
            save_model_graphs(netron_url=f"http://{HOST}:{port}",
                              out_paths=output,
                              horizontal_mode=horizontal_mode,
                              timeout=timeout))

    except (OSError, PermissionError) as err:
        # Port is already in use or socket was not available (we do not rely on the error numbers because they are OS-dependent).
        # The first condition occurs on Linux, the second one on Windows.
        if "Address already in use" in str(
                err) or "An attempt was made to access a socket in a way forbidden by its access permissions" in str(
                    err):
            print(f"Exception encountered: {err}")
            if allowed_port_trials <= 1:
                print("Could not find a port to open netron on")
                return
            new_port = random.randrange(10000, 65000)  # Try out another port randomly
            print(f"Trying out with another port {new_port}")

            # Not sure if this is needed but we make sure that the failing netron instance is closed
            netron.stop()

            # Call same function with a reduced allowed_port_trials
            export_graph(model_path=model_path,
                         output=output,
                         horizontal_mode=horizontal_mode,
                         port=new_port,
                         timeout=timeout,
                         allowed_port_trials=allowed_port_trials - 1)
        else:
            raise err
    finally:
        # Stops the netron server
        netron.stop()


def main():
    """
    Calls the main function of the package after parsing the arguments
    """
    argparser = argparse.ArgumentParser()
    argparser.add_argument("model_path", help="Path to model file (onnx, pt, etc.)")
    argparser.add_argument("--output",
                           "-o",
                           default="./network.png",
                           help="Output file to be written (either svg or png)")
    argparser.add_argument("--horizontal",
                           "-ho",
                           action="store_true",
                           help="Display the graph horizontally (rather than vertically by default)")
    argparser.add_argument("--timeout", "-t", default=5000, type=int, help="Timeout for requests in ms")
    argparser.add_argument("--port",
                           "-p",
                           default=8487,
                           type=int,
                           help="Port that will be used to serve the Netron app")
    args = argparser.parse_args()

    export_graph(args.model_path, [args.output], args.horizontal, args.port, args.timeout)
