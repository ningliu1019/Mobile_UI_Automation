import os
import time

import allure
from selenium.common.exceptions import InvalidSessionIdException, NoSuchElementException, NoSuchWindowException, TimeoutException

# Injected into new tabs immediately after switch — the CDP
# Page.addScriptToEvaluateOnNewDocument registered during driver creation only
# covers the original tab; new tabs are a fresh CDP target with no protection.
_REDIRECT_BLOCKER_JS = r"""
(function() {
    var b = function(u) { return /^(twitch|intent):\/\//i.test(String(u)); };
    var d = Object.getOwnPropertyDescriptor(Location.prototype, 'href');
    if (d && d.set) {
        Object.defineProperty(Location.prototype, 'href', {
            get: d.get,
            set: function(u) { if (!b(u)) d.set.call(this, u); },
            configurable: true
        });
    }
    ['assign', 'replace'].forEach(function(fn) {
        var o = Location.prototype[fn];
        Location.prototype[fn] = function(u) { if (!b(u)) o.call(this, u); };
    });
})();
"""
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class BasePage:
    """Base class for all page objects. Provides shared wait, scroll,
    and screenshot utilities so individual pages stay focused on their own
    locators and actions."""

    def __init__(self, driver: WebDriver, config: dict):
        self.driver = driver
        self.config = config
        self._timeout = config.get("browser", {}).get("explicit_wait", 20)

    # ------------------------------------------------------------------
    # Wait helpers
    # ------------------------------------------------------------------

    def wait_for_element(self, locator: tuple, timeout: int = None) -> WebElement:
        t = timeout or self._timeout
        return WebDriverWait(self.driver, t).until(
            EC.element_to_be_clickable(locator)
        )

    def wait_for_elements(self, locator: tuple, timeout: int = None) -> list:
        t = timeout or self._timeout
        return WebDriverWait(self.driver, t).until(
            EC.presence_of_all_elements_located(locator)
        )

    def wait_for_element_any(self, locators: list, timeout: int = None) -> WebElement:
        """Return the first element that becomes clickable from a list of locators."""
        t = timeout or self._timeout
        deadline = time.time() + t

        while time.time() < deadline:
            for locator in locators:
                try:
                    el = self.driver.find_element(*locator)
                    if el.is_displayed():
                        return el
                except Exception:
                    pass
            time.sleep(0.3)

        raise TimeoutException(
            f"None of the following locators were found within {t}s: {locators}"
        )

    def is_present(self, locator: tuple, timeout: int = 5) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return True
        except (TimeoutException, NoSuchWindowException, InvalidSessionIdException):
            return False

    # ------------------------------------------------------------------
    # Interaction helpers
    # ------------------------------------------------------------------

    def scroll_down(self, pixels: int = 600) -> None:
        """Scroll down by *pixels*.

        Modern SPAs — including Twitch — pin ``overflow: hidden`` on
        ``<html>`` / ``<body>`` and scroll a child container div instead.
        ``window.scrollBy()`` has no effect in that layout.

        This helper walks up the DOM from the first ``<article>`` / ``<main>``
        element to find the nearest element that actually has
        ``overflow: scroll | auto`` and a scrollable height, then scrolls that
        container.  Falls back to ``window.scrollBy`` for plain pages.
        """
        self.driver.execute_script("""
            (function(px) {
                function findScrollable(el) {
                    while (el && el !== document.documentElement) {
                        var oy = window.getComputedStyle(el).overflowY;
                        if ((oy === 'scroll' || oy === 'auto') &&
                                el.scrollHeight > el.clientHeight) {
                            return el;
                        }
                        el = el.parentElement;
                    }
                    return null;
                }
                var seed = document.querySelector('article, main, [role="main"]');
                var container = seed ? findScrollable(seed.parentElement) : null;
                if (container) {
                    container.scrollTop += px;
                } else {
                    window.scrollBy(0, px);
                }
            })(arguments[0]);
        """, pixels)

    def hard_refresh(self) -> None:
        """Force a full cache-bypass reload (equivalent to Ctrl+Shift+R).

        Ensures the browser re-sends all request headers — including the
        mobile User-Agent set by Chrome's device emulation — on every
        resource request.  Blocks until ``document.readyState == 'complete'``.
        """
        self.driver.execute_script("location.reload(true);")
        WebDriverWait(self.driver, 15).until(
            lambda d: d.execute_script("return document.readyState;") == "complete"
        )

    def click_and_switch_window(self, element: WebElement, timeout: int = 8) -> None:
        """Click *element* and switch focus to any new tab/window it opens.

        Mobile Twitch opens streamer pages in a new tab. Without this,
        Selenium stays on the (now-closed) original tab and every subsequent
        call raises NoSuchWindowException.

        If no new window appears within *timeout* seconds, the click is still
        performed but the driver stays on the current window.
        """
        original_handle = self.driver.current_window_handle
        original_handles = set(self.driver.window_handles)

        element.click()

        try:
            # Wait until a new window handle appears
            WebDriverWait(self.driver, timeout).until(
                lambda d: set(d.window_handles) - original_handles
            )
            new_handles = set(self.driver.window_handles) - original_handles
            self.driver.switch_to.window(next(iter(new_handles)))
            # Re-apply the twitch:// redirect blocker on the new tab.
            # CDP addScriptToEvaluateOnNewDocument is per-target; the script
            # registered at driver creation only covers the original tab.
            # execute_cdp_cmd registers it for future navigations (hard refresh),
            # execute_script patches the already-loaded page immediately.
            try:
                self.driver.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument",
                    {"source": _REDIRECT_BLOCKER_JS},
                )
                self.driver.execute_script(_REDIRECT_BLOCKER_JS)
            except Exception:
                pass
        except TimeoutException:
            # No new window — navigation happened in the same tab, nothing to do
            pass

    def dismiss_if_present(self, locator: tuple, timeout: int = 4) -> bool:
        """Click an element if it exists; silently skip if not found."""
        if not self.is_present(locator, timeout):
            return False
        try:
            self.driver.find_element(*locator).click()
            return True
        except (NoSuchElementException, Exception):
            return False

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def take_screenshot(self, name: str = "screenshot") -> str:
        directory = self.config.get("screenshots", {}).get("directory", "screenshots")
        os.makedirs(directory, exist_ok=True)

        timestamp = int(time.time())
        filepath = os.path.join(directory, f"{name}_{timestamp}.png")
        self.driver.save_screenshot(filepath)

        with open(filepath, "rb") as fh:
            allure.attach(
                fh.read(),
                name=name,
                attachment_type=allure.attachment_type.PNG,
            )

        return filepath
