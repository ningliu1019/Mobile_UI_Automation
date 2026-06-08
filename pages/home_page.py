import allure
from selenium.webdriver.common.by import By

from common.modal_handler import ModalHandler
from pages.base_page import BasePage


class HomePage(BasePage):
    """Twitch landing page (mobile WAP).

    Verified navigation flow (from screen recording 2025-06-08):
        The bottom nav has a Browse button (href="/directory").
        Clicking it navigates to /directory which exposes the search input.
        There is NO separate /search page on this WAP build.

        Step 1 (HomePage):  click Browse  → lands on /directory
        Step 2 (SearchPage): search input is now visible, type query
    """

    # --- Bottom navigation — Browse button ---
    # Confirmed from DevTools Recorder (2025-06-08):
    #   selector: a:nth-of-type(2)  /  aria-label: "瀏覽"
    #   xpath:    //*[@id="root"]/div[2]/a[2]
    #
    # We prefer href="/directory" (structural, locale-independent) over the
    # positional nth-of-type and over the Chinese aria-label (breaks on EN builds).
    _BROWSE_BUTTON = (By.CSS_SELECTOR, 'a[href="/directory"]')       # primary
    _BROWSE_ARIA   = (By.CSS_SELECTOR, 'a[aria-label="瀏覽"]')        # zh-TW fallback
    _BROWSE_ARIA_EN = (By.CSS_SELECTOR, 'a[aria-label="Browse"]')    # EN fallback

    def __init__(self, driver, config: dict):
        super().__init__(driver, config)
        self._url: str = config.get("twitch", {}).get("url", "https://www.twitch.tv")
        self._modals = ModalHandler(driver, config)

    @allure.step("Navigate to Twitch homepage")
    def navigate(self) -> "HomePage":
        self.driver.get(self._url)
        self._modals.dismiss_cookie_banner()
        return self

    @allure.step("Click Browse to open search")
    def click_search(self) -> None:
        """On Twitch mobile WAP the Browse (/directory) button is the search entry point.
        Clicking it navigates to /directory where the search input is exposed.
        """
        self.wait_for_element_any(
            [self._BROWSE_BUTTON, self._BROWSE_ARIA, self._BROWSE_ARIA_EN]
        ).click()
