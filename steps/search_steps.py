import allure
from selenium.webdriver.remote.webdriver import WebDriver

from pages.search_page import SearchPage


class SearchSteps:
    """Reusable search and result-navigation actions."""

    def __init__(self, driver: WebDriver, config: dict):
        self._search = SearchPage(driver, config)

    @allure.step("Search for '{query}'")
    def search_for(self, query: str) -> None:
        """Type *query* and press Enter to navigate to the game category page."""
        self._search.type_query(query)

    @allure.step("Scroll search results {count} time(s)")
    def scroll_results(self, count: int) -> None:
        self._search.scroll_results(count)

    @allure.step("Select the streamer at the top of the current screen")
    def select_top_streamer(self) -> str:
        """Open the live streamer at the top of the viewport; return its name.

        Matches the assignment spec: "scroll down 2 times → select one streamer".
        """
        return self._search.select_top_visible_streamer()

    @allure.step("Click 頻道 (Channels) tab")
    def click_channels_tab(self) -> None:
        """Filter search results to channels."""
        self._search.click_channels_tab()

    @allure.step("Search '{query}', scroll {scroll_count}x, then open top streamer")
    def search_scroll_and_pick(
        self, query: str, scroll_count: int
    ) -> str:
        """Full search-to-streamer flow (assignment spec):
        type + Enter → click 頻道 tab → scroll → open the top live streamer.
        Returns the chosen channel name.
        """
        self.search_for(query)
        self.click_channels_tab()
        self.scroll_results(scroll_count)
        return self.select_top_streamer()
