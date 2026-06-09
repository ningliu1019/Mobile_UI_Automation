import allure
from selenium.webdriver.remote.webdriver import WebDriver

from pages.streamer_page import StreamerPage


class StreamerSteps:
    """Reusable actions for any live streamer / channel page.

    Handles the common post-navigation pattern: dismiss pop-ups,
    wait for the stream to settle, then capture evidence.
    Any test landing on a streamer page can reuse these steps.
    """

    def __init__(self, driver: WebDriver, config: dict):
        self._streamer = StreamerPage(driver, config)

    @allure.step("Dismiss pop-ups on streamer page")
    def dismiss_popups(self) -> None:
        self._streamer.dismiss_popups()

    @allure.step("Wait for streamer page to fully load")
    def wait_for_load(self) -> None:
        self._streamer.wait_for_load()

    @allure.step("Capture screenshot of streamer page")
    def capture_screenshot(self) -> str:
        return self._streamer.capture_screenshot()

    @allure.step("Handle pop-ups, wait for load, verify player, and capture screenshot")
    def view_and_verify(self) -> dict:
        """Full post-navigation flow in one reusable step.

        Dismisses pop-ups, waits for the player, captures a screenshot, and
        returns a status dict for the test to assert on:
            {url, player_present, player_error, video_playing, screenshot}
        """
        self.dismiss_popups()
        self.wait_for_load()
        status = self._streamer.status()
        status["screenshot"] = self.capture_screenshot()
        return status
