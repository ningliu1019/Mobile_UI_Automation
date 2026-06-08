"""modal_handler.py — centralised pop-up and modal dismissal.

All Twitch overlay selectors live here so that:
  • a selector change requires one edit, not a grep across pages/steps
  • any page or step can dismiss any modal without duplicating logic

Usage
-----
    from common.modal_handler import ModalHandler

    modals = ModalHandler(driver, config)
    modals.dismiss_cookie_banner()
    modals.dismiss_mature_content()
    modals.dismiss_any()          # tries everything in priority order
"""

import allure
from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class ModalHandler(BasePage):
    """Handles all known pop-ups and modals across the Twitch WAP experience."""

    # ------------------------------------------------------------------ #
    # Locators — one place to update when Twitch changes its DOM          #
    # ------------------------------------------------------------------ #

    # GDPR / cookie consent banner (appears on first visit)
    _COOKIE_ACCEPT = (By.CSS_SELECTOR, '[data-a-target="consent-banner-accept"]')

    # Mature-content gate on certain streamer pages ("Start Watching")
    _MATURE_CONTENT_ACCEPT = (By.CSS_SELECTOR,
                               '[data-a-target="player-overlay-mature-accept"]')

    # Generic modal close buttons
    _ARIA_CLOSE = (By.CSS_SELECTOR, 'button[aria-label="Close"]')
    _DATA_CLOSE = (By.CSS_SELECTOR, '[data-a-target="modal-close-button"]')

    # "Get the App" interstitial sometimes shown on mobile WAP
    _APP_PROMPT_DISMISS = (By.CSS_SELECTOR,
                            'button[data-a-target="dismiss-app-prompt"]')

    # Age-gate / login-required overlay
    _AGE_GATE_CONFIRM = (By.CSS_SELECTOR, '[data-a-target="age-gate-confirm"]')

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    @allure.step("Dismiss cookie / consent banner")
    def dismiss_cookie_banner(self) -> bool:
        return self.dismiss_if_present(self._COOKIE_ACCEPT, timeout=2)

    @allure.step("Dismiss mature-content warning")
    def dismiss_mature_content(self) -> bool:
        return self.dismiss_if_present(self._MATURE_CONTENT_ACCEPT, timeout=2)

    @allure.step("Dismiss 'Get the App' prompt")
    def dismiss_app_prompt(self) -> bool:
        return self.dismiss_if_present(self._APP_PROMPT_DISMISS, timeout=2)

    @allure.step("Dismiss age gate")
    def dismiss_age_gate(self) -> bool:
        return self.dismiss_if_present(self._AGE_GATE_CONFIRM, timeout=2)

    @allure.step("Close generic modal")
    def close_modal(self) -> bool:
        """Try the most common close-button patterns in order."""
        for locator in (self._ARIA_CLOSE, self._DATA_CLOSE):
            if self.dismiss_if_present(locator, timeout=2):
                return True
        return False

    @allure.step("Dismiss any pop-up or modal")
    def dismiss_any(self) -> None:
        """Check for all known overlays and dismiss any that are present.

        Each check has a short 2s timeout — if nothing appears it moves on
        immediately so no time is wasted when (as is common) no pop-up shows.
        """
        self.dismiss_cookie_banner()
        self.dismiss_age_gate()
        self.dismiss_mature_content()
        self.dismiss_app_prompt()
        self.close_modal()
