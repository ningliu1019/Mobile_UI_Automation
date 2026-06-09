import time

import allure
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    InvalidSessionIdException,
    NoSuchElementException,
    NoSuchWindowException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from common.modal_handler import ModalHandler
from pages.base_page import BasePage


class StreamerPage(BasePage):
    """Individual Twitch live streamer page (mobile WAP).

    Confirmed live selectors (2025-06-09):
      [data-a-target="video-player"] → present and visible ✓
      <video> → present once the HLS player initialises ✓
    """

    _PLAYER_CONTAINER = (By.CSS_SELECTOR, '[data-a-target="video-player"]')
    _LOAD_INDICATORS = [
        _PLAYER_CONTAINER,
        (By.CSS_SELECTOR, '[data-a-target="player-overlay-background"]'),
        (By.CSS_SELECTOR, ".player-overlay"),
    ]
    _VIDEO = (By.CSS_SELECTOR, "video")
    _UNMUTE = (By.XPATH, "//button[@aria-label='Unmute']")

    def __init__(self, driver, config: dict):
        super().__init__(driver, config)
        self._modals = ModalHandler(driver, config)
        twitch_cfg = config.get("twitch", {})
        self._buffer_seconds = twitch_cfg.get("stream_buffer_seconds", 30)
        self._video_wait = twitch_cfg.get("video_wait_seconds", 20)

    @allure.step("Dismiss pop-ups and modals on streamer page")
    def dismiss_popups(self) -> "StreamerPage":
        self._modals.dismiss_any()
        return self

    @allure.step("Wait for the streamer page and player to load")
    def wait_for_load(self) -> "StreamerPage":
        # No hard refresh here: the homepage navigation already refreshed to
        # activate mobile emulation, and the channel URL is the mobile host, so
        # the player loads directly. Just wait for it to render and start playing:
        # player container → clear overlays → <video> → unmute → playback.
        self._wait_for_player_container()
        self._modals.dismiss_any()
        self._wait_for_video_element()
        self._try_unmute()
        self._await_playback_or_error(self._buffer_seconds)
        return self

    @allure.step("Capture streamer page screenshot")
    def capture_screenshot(self) -> str:
        return self.take_screenshot("streamer_page")

    # ------------------------------------------------------------------
    # Status / verification
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Snapshot of the streamer page for test assertions.

        - ``player_present``: the video-player container rendered (proof we
          reached the streamer page).
        - ``player_error``: any player error code (e.g. ``"#3000"``) shown, else "".
        - ``video_playing``: True if the <video> playhead advances (the stream
          is actually decoding and playing).
        """
        return {
            "url": self._current_url(),
            "player_present": self.is_player_present(timeout=5),
            "player_error": self.player_error(),
            "video_playing": self.is_video_advancing(),
        }

    def is_player_present(self, timeout: int = 5) -> bool:
        """True if the Twitch video-player container is in the DOM."""
        return self.is_present(self._PLAYER_CONTAINER, timeout)

    def player_error(self) -> str:
        """Return the player error code shown in a decode-error overlay
        (e.g. ``"#3000"``), or ``""``. Matches zh-TW ("錯誤代碼 #3000") and
        EN ("Error #3000")."""
        try:
            return self.driver.execute_script(r"""
                var b = document.body ? (document.body.innerText || '') : '';
                var m = b.match(/(?:錯誤代碼|Error)\s*#?\s*(\d{3,4})/i);
                return m ? ('#' + m[1]) : '';
            """) or ""
        except (NoSuchWindowException, InvalidSessionIdException):
            return ""

    def is_video_advancing(self, checks: int = 3, interval: float = 1.5) -> bool:
        """True if the <video> currentTime advances across successive samples,
        i.e. the stream is actually decoding and playing (not just buffered)."""
        prev = self._current_time()
        for _ in range(checks):
            time.sleep(interval)
            cur = self._current_time()
            if cur > prev + 0.3:
                return True
            prev = max(prev, cur)
        return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _current_url(self) -> str:
        try:
            return self.driver.current_url
        except (NoSuchWindowException, InvalidSessionIdException):
            return ""

    def _current_time(self) -> float:
        """Current playback position of the <video> element, or 0.0."""
        try:
            t = self.driver.execute_script(
                "var v=document.querySelector('video');return v?v.currentTime:0;"
            )
            return float(t or 0)
        except (NoSuchWindowException, InvalidSessionIdException, ValueError, TypeError):
            return 0.0

    def _await_playback_or_error(self, timeout: float) -> None:
        """Block until the video starts advancing OR the player shows an error,
        up to *timeout* seconds. Returns early on either outcome."""
        deadline = time.time() + timeout
        prev = self._current_time()
        while time.time() < deadline:
            if self.player_error():
                return
            cur = self._current_time()
            if cur > prev + 0.3:
                return
            prev = max(prev, cur)
            time.sleep(1.0)

    def _wait_for_video_element(self) -> None:
        try:
            WebDriverWait(self.driver, self._video_wait).until(
                EC.presence_of_element_located(self._VIDEO)
            )
        except (TimeoutException, NoSuchWindowException, InvalidSessionIdException):
            pass

    def _try_unmute(self) -> None:
        """Unmute if the player started muted (common on autoplay)."""
        try:
            self.driver.find_element(*self._UNMUTE).click()
        except (NoSuchElementException, StaleElementReferenceException,
                ElementClickInterceptedException, ElementNotInteractableException,
                NoSuchWindowException, InvalidSessionIdException):
            pass

    def _wait_for_player_container(self) -> None:
        """Wait until any player-container indicator is present; stay silent on
        timeout / a closed tab (status()/assertions surface a real failure)."""
        for locator in self._LOAD_INDICATORS:
            try:
                WebDriverWait(self.driver, self._timeout).until(
                    EC.presence_of_element_located(locator)
                )
                return
            except (TimeoutException, NoSuchWindowException, InvalidSessionIdException):
                continue
