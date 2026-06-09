import allure
from selenium.webdriver.remote.webdriver import WebDriver

from pages.home_page import HomePage


class NavigationSteps:
    """Reusable navigation actions built on top of HomePage.

    Any test that needs to land on Twitch or open the search panel
    can import and call these steps without touching page internals.
    """

    def __init__(self, driver: WebDriver, config: dict):
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
