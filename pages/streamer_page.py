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

    # Confirmed live selectors (2026-06-09):
    #   [data-a-target="video-player"] → present and visible ✓
    #   .video-player, stream-info-card-component, h1 → absent ✗
    _LOAD_INDICATORS = [
        (By.CSS_SELECTOR, '[data-a-target="video-player"]'),
        (By.CSS_SELECTOR, '[data-a-target="player-overlay-background"]'),
        (By.CSS_SELECTOR, ".player-overlay"),
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
        # Wait for the player container to confirm the SPA has rendered.
        for locator in self._LOAD_INDICATORS:
            try:
                WebDriverWait(self.driver, self._timeout).until(
                    EC.presence_of_element_located(locator)
                )
                break
            except Exception:
                continue

        # Hard-refresh after the SPA renders: the initial navigation may have
        # served desktop-cached resources before mobile emulation fully applied.
        # A cache-bypass reload forces Twitch to re-serve the mobile WAP player.
        # Wrapped in try/except: if a twitch:// redirect slipped through before
        # the blocker was injected, the window may already be gone.
        try:
            self.hard_refresh()
        except Exception:
            pass

        # Re-wait for the player container after the refresh — the SPA must
        # render again on the reloaded page before the video element appears.
        for locator in self._LOAD_INDICATORS:
            try:
                WebDriverWait(self.driver, self._timeout).until(
                    EC.presence_of_element_located(locator)
                )
                break
            except Exception:
                continue

        # After the hard refresh, overlays such as "Open in App", mature-content
        # gate, and cookie banners reappear.  Dismiss them before waiting for
        # the player so they don't block autoplay or the <video> element.
        self._modals.dismiss_any()

        # Wait for the <video> element to appear in the DOM (up to 20s).
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "video"))
            )
        except Exception:
            pass

        # Unmute if the player started muted (common on autoplay).
        try:
            unmute_btn = self.driver.find_element(
                By.XPATH, "//button[@aria-label='Unmute']"
            )
            unmute_btn.click()
        except Exception:
            pass

        # Give the HLS stream 30s to buffer, then capture a verification
        # screenshot to confirm the player rendered correctly before the test
        # proceeds to its own evidence screenshot.
        time.sleep(30)
        self.take_screenshot("player_load_verification")

        return self

    @allure.step("Capture streamer page screenshot")
    def capture_screenshot(self) -> str:
        return self.take_screenshot("streamer_page")
