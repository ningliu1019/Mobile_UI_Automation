import allure
from selenium.webdriver.remote.webdriver import WebDriver

from pages.home_page import HomePage


class NavigationSteps:
    """Reusable navigation actions built on top of HomePage.

    Any test that needs to land on Twitch or open the search panel
    can import and call these steps without touching page internals.
    """

    def __init__(self, driver: WebDriver, config: dict):
        self._driver = driver
        self._config = config
        self._home = HomePage(driver, config)

    @allure.step("Open Twitch homepage")
    def open_twitch(self) -> None:
        self._home.navigate()

    @allure.step("Open search panel")
    def open_search(self) -> None:
        self._home.click_search()

    @allure.step("Open Twitch and go to search")
    def open_twitch_and_search(self) -> None:
        """Convenience combo — navigate then open search in one call."""
        self.open_twitch()
        self.open_search()

    @allure.step("Verify page is in WAP (mobile emulator) mode")
    def verify_wap_mode(self) -> dict:
        """Assert the viewport width matches the configured device and return dimensions.

        Raises AssertionError if the browser is not in mobile emulation —
        useful as a guard at the start of any WAP test.
        """
        viewport = self._driver.execute_script(
            "return {width: window.innerWidth, height: window.innerHeight}"
        )
        expected_width = self._config.get("device", {}).get("width", 390)

        assert viewport["width"] <= expected_width + 20, (
            f"Viewport width {viewport['width']}px is too wide for WAP mode. "
            f"Expected ≤{expected_width + 20}px — verify mobile emulation is active."
        )
        return viewport
