import json
import logging
import os
import platform
import re
from typing import Any

import undetected as uc
from selenium.webdriver.chrome.webdriver import WebDriver
from seleniumwire import ProxyConfig, SeleniumWireOptions
from wire import UndetectedChrome

logger = logging.getLogger(__name__)

FLARESOLVERR_VERSION = None
PLATFORM_VERSION = None
USER_AGENT = None
XVFB_DISPLAY = None


def get_config_log_html() -> bool:
    return os.environ.get("LOG_HTML", "false").lower() == "true"


def get_config_headless() -> bool:
    return os.environ.get("HEADLESS", "true").lower() == "true"


def get_config_disable_media() -> bool:
    return os.environ.get("DISABLE_MEDIA", "false").lower() == "true"


def get_flaresolverr_version() -> str:
    global FLARESOLVERR_VERSION
    if FLARESOLVERR_VERSION is not None:
        return FLARESOLVERR_VERSION

    package_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), os.pardir, "package.json"
    )
    if not os.path.isfile(package_path):
        package_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "package.json"
        )
    with open(package_path) as f:
        FLARESOLVERR_VERSION = json.loads(f.read())["version"]
        return FLARESOLVERR_VERSION


def get_current_platform() -> str:
    global PLATFORM_VERSION
    if PLATFORM_VERSION is not None:
        return PLATFORM_VERSION
    PLATFORM_VERSION = os.name
    return PLATFORM_VERSION


def get_webdriver(proxy: dict[str, Any] | None = None) -> WebDriver:
    logger.debug("Launching web browser...")

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-search-engine-choice-screen")
    # todo: this param shows a warning in chrome head-full
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # this option removes the zygote sandbox (it seems that the resolution is a bit faster)
    options.add_argument("--no-zygote")
    # attempt to fix Docker ARM32 build
    IS_ARMARCH = platform.machine().startswith(("arm", "aarch"))
    if IS_ARMARCH:
        options.add_argument("--disable-gpu-sandbox")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")

    language = os.environ.get("LANG", None)
    if language is not None:
        options.add_argument("--accept-lang=%s" % language)

    # Fix for Chrome 117 | https://github.com/FlareSolverr/FlareSolverr/issues/910
    if USER_AGENT is not None:
        options.add_argument("--user-agent=%s" % USER_AGENT)

    # note: headless mode is detected (headless = True)
    # we launch the browser in head-full mode with the window hidden
    windows_headless = False
    if get_config_headless():
        if os.name == "nt":
            windows_headless = True
        else:
            start_xvfb_display()

    seleniumwire_options = None
    if proxy and "url" in proxy:
        if not isinstance(proxy["url"], str):
            raise ValueError("Proxy URL must be a string")

        upstream_proxy_kwargs = {}
        key = "https" if proxy["url"].startswith("https") else "http"
        to_strip = len(key) + 3  # length of "http://" or "https://"

        if "username" in proxy and "password" in proxy:
            upstream_proxy_kwargs[key] = (
                f"{key}://{proxy['username']}:{proxy['password']}@{proxy['url'][to_strip:]}"
            )
        else:
            upstream_proxy_kwargs[key] = proxy["url"]

        logger.info(f"Using upstream proxy: {upstream_proxy_kwargs[key]}")
        seleniumwire_options = SeleniumWireOptions(
            upstream_proxy=ProxyConfig(**upstream_proxy_kwargs)
        )
    try:
        chrome_kwargs = {
            "options": options,
            "windows_headless": windows_headless,
            "headless": get_config_headless(),
            "enable_cdp_events": True
        }
        if seleniumwire_options is not None:
            chrome_kwargs["seleniumwire_options"] = seleniumwire_options

        driver = UndetectedChrome(**chrome_kwargs)
    except Exception as e:
        logger.error("Error starting Chrome: %s" % e)
        # No point in continuing if we cannot retrieve the driver
        raise e

    return driver


def get_user_agent(driver=None) -> str:
    global USER_AGENT
    if USER_AGENT is not None:
        return USER_AGENT

    created_driver = False
    try:
        if driver is None:
            driver = get_webdriver()
            created_driver = True
        USER_AGENT = driver.execute_script("return navigator.userAgent")
        # Fix for Chrome 117 | https://github.com/FlareSolverr/FlareSolverr/issues/910
        USER_AGENT = re.sub("HEADLESS", "", USER_AGENT, flags=re.IGNORECASE)
        return USER_AGENT
    except Exception as e:
        raise e
    finally:
        if created_driver and driver is not None:
            if PLATFORM_VERSION == "nt":
                driver.close()
            driver.quit()


def start_xvfb_display():
    global XVFB_DISPLAY
    if XVFB_DISPLAY is None:
        from xvfbwrapper import Xvfb

        XVFB_DISPLAY = Xvfb()
        XVFB_DISPLAY.start()


def object_to_dict(_object):
    json_dict = json.loads(json.dumps(_object, default=lambda o: o.__dict__))
    # remove hidden fields
    return {k: v for k, v in json_dict.items() if not k.startswith("__")}
