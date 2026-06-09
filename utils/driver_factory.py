import os
import platform
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class DriverFactory:
    """Creates and configures a Chrome WebDriver with mobile emulation."""

    # Per-OS default install locations of the *real* Google Chrome binary.
    # The real binary ships a licensed H.264 decoder; ChromeDriver's bundled
    # Chromium lacks it and Twitch HLS (H.264) fails with error #3000.
    _CHROME_BINARIES = {
        "Darwin": [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ],
        "Windows": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
        "Linux": [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/opt/google/chrome/chrome",
        ],
    }

    @staticmethod
    def create_driver(config: dict) -> webdriver.Chrome:
        options = DriverFactory._build_options(config)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Register an anti-detection script that runs before any page JS on
        # every navigation in this tab:
        #  1. Delete ChromeDriver's cdc_* fingerprint variables.
        #  2. Mask navigator.webdriver.
        #  3. Block twitch:// / intent:// redirects that would close the tab.
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": r"""
                (function() {
                    for (var k of Object.getOwnPropertyNames(window)) {
                        if (k.startsWith('cdc_')) {
                            try { delete window[k]; } catch(e) {}
                        }
                    }
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                        configurable: true
                    });
                    var _blocked = function(u) {
                        return /^(twitch|intent):\/\//i.test(String(u));
                    };
                    var _d = Object.getOwnPropertyDescriptor(Location.prototype, 'href');
                    if (_d && _d.set) {
                        Object.defineProperty(Location.prototype, 'href', {
                            get: _d.get,
                            set: function(u) { if (!_blocked(u)) _d.set.call(this, u); },
                            configurable: true
                        });
                    }
                    ['assign', 'replace'].forEach(function(fn) {
                        var _orig = Location.prototype[fn];
                        Location.prototype[fn] = function(u) {
                            if (!_blocked(u)) _orig.call(this, u);
                        };
                    });
                    var _wo = window.open;
                    window.open = function(u) { if (u && _blocked(u)) return null; return _wo.apply(window, arguments); };
                })();
            """
        })

        browser_cfg = config.get("browser", {})
        driver.implicitly_wait(0)  # keep 0 — see comment in _build_options
        driver.set_page_load_timeout(browser_cfg.get("page_load_timeout", 30))

        return driver

    @staticmethod
    def _build_options(config: dict) -> Options:
        options = Options()

        # Real Google Chrome binary — includes licensed H.264 decoder.
        # ChromeDriver's bundled Chromium lacks H.264; Twitch HLS streams use
        # H.264 and fail with error #3000 (decode error) on Chromium builds.
        binary = DriverFactory._chrome_binary(config)
        if binary:
            options.binary_location = binary

        mobile_emulation = DriverFactory._mobile_emulation(config)
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        # NOTE: the User-Agent is set by the mobileEmulation profile itself
        # (deviceName carries its own UA; custom metrics carry "userAgent").
        # A separate --user-agent arg is therefore redundant and would even
        # contradict a named device, so it is intentionally not added here.

        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("prefs", {
            "protocol_handler.excluded_schemes": {"twitch": True},
        })
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--autoplay-policy=no-user-gesture-required")

        browser_cfg = config.get("browser", {})
        if browser_cfg.get("headless", False):
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")

        return options

    @staticmethod
    def _chrome_binary(config: dict) -> Optional[str]:
        """Resolve the real Google Chrome binary path in a cross-platform way.

        Order of precedence:
          1. ``browser.chrome_binary`` config override (any OS / custom install).
          2. The first existing per-OS default location.
          3. ``None`` — let Selenium locate Chrome on PATH as a last resort.
        """
        configured = config.get("browser", {}).get("chrome_binary")
        if configured:
            return configured

        for candidate in DriverFactory._CHROME_BINARIES.get(platform.system(), []):
            if os.path.exists(candidate):
                return candidate

        return None

    @staticmethod
    def _mobile_emulation(config: dict) -> dict:
        device_cfg = config.get("device", {})

        if device_cfg.get("use_named_device", True):
            return {"deviceName": device_cfg.get("name", "iPhone 12 Pro")}

        return {
            "deviceMetrics": {
                "width": device_cfg.get("width", 390),
                "height": device_cfg.get("height", 844),
                "pixelRatio": device_cfg.get("pixel_ratio", 3.0),
            },
            "userAgent": device_cfg.get("user_agent", ""),
        }
