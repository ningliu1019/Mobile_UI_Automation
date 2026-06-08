import time

import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from common.modal_handler import ModalHandler
from pages.base_page import BasePage


class StreamerPage(BasePage):
    """Individual Twitch streamer / channel page (mobile WAP).

    Owns only streamer-page locators and load detection.
    All modal/pop-up dismissal is delegated to ModalHandler.
    """

    # --- Page-load indicators ---
    _LOAD_INDICATORS = [
        (By.CSS_SELECTOR, ".video-player"),
        (By.CSS_SELECTOR, '[data-a-target="video-player"]'),
        (By.CSS_SELECTOR, '[data-a-target="stream-info-card-component"]'),
        (By.CSS_SELECTOR, "h1"),   # channel name always renders
    ]

    def __init__(self, driver, config: dict):
        super().__init__(driver, config)
        self._modals = ModalHandler(driver, config)

    @allure.step("Dismiss pop-ups and modals on streamer page")
    def dismiss_popups(self) -> "StreamerPage":
        self._modals.dismiss_any()
        return self

    @allure.step("Wait for streamer page to fully load")
    def wait_for_load(self) -> "StreamerPage":
        for locator in self._LOAD_INDICATORS:
            try:
                WebDriverWait(self.driver, self._timeout).until(
                    EC.presence_of_element_located(locator)
                )
                break
            except Exception:
                continue

        # Allow media / lazy assets a moment to settle before screenshotting
        time.sleep(2)
        return self

    @allure.step("Capture streamer page screenshot")
    def capture_screenshot(self) -> str:
        return self.take_screenshot("streamer_page")
