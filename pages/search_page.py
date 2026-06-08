import time

import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage


class SearchPage(BasePage):
    """Twitch search / browse page (mobile WAP — m.twitch.tv/directory).

    Confirmed flow from DevTools Recorder (2025-06-08):
      1. After clicking Browse the search input is inside #twilight-sticky-header-root
      2. Type query then press Enter → navigates to game category page
      3. Streamer cards are <article> > <button> > <img src="live_user_*">
      4. After scrolling, "select streamer" means the card at the TOP of the
         current viewport — not necessarily index 0 of the full list.
    """

    # ------------------------------------------------------------------
    # Search input
    # Confirmed: <input data-a-target="tw-input" aria-label="搜尋" type="search">
    #            inside #twilight-sticky-header-root
    # ------------------------------------------------------------------
    _SEARCH_INPUTS = [
        (By.CSS_SELECTOR, '[data-a-target="tw-input"]'),          # ✅ Twitch test hook
        (By.CSS_SELECTOR, '#twilight-sticky-header-root input'),  # ✅ confirmed container
        (By.CSS_SELECTOR, 'input[type="search"]'),                # ✅ HTML semantic
        (By.CSS_SELECTOR, 'input[placeholder="搜尋"]'),           # ✅ zh-TW placeholder
        (By.CSS_SELECTOR, 'input[placeholder*="搜索"]'),          # zh-CN fallback
        (By.CSS_SELECTOR, 'input[placeholder*="Search"]'),        # EN fallback
    ]

    # ------------------------------------------------------------------
    # 頻道 (Channels) tab — confirmed from live DOM (2025-06-08):
    #   <a role="tab" data-index="1" href="/search?term=...&type=channels">
    #     <div>頻道</div>
    #   </a>
    #
    # href*="type=channels" is the best selector:
    #   • functional URL parameter — not a display string, not a class hash
    #   • locale-independent (works in EN / zh-TW / zh-CN builds)
    # ------------------------------------------------------------------
    _CHANNELS_TAB = [
        (By.CSS_SELECTOR, 'a[href*="type=channels"]'),          # ✅ confirmed — best
        (By.CSS_SELECTOR, 'a[role="tab"][data-index="1"]'),     # ✅ confirmed — fallback
        (By.XPATH, '//a[@role="tab" and contains(@href,"type=channels")]'),
    ]

    # ------------------------------------------------------------------
    # Streamer cards
    # Confirmed: <article> > <button> > <div> > <div> > <img src="live_user_*">
    # ------------------------------------------------------------------
    _CHANNEL_CARD_SELECTORS = [
        (By.CSS_SELECTOR, 'article button:has(img[src*="live_user"])'),       # ✅ confirmed
        (By.XPATH, '//article//button[.//img[contains(@src,"live_user")]]'),  # XPath equiv
        (By.CSS_SELECTOR, 'button.tw-link:has(img[src*="live_user"])'),       # fallback
        (By.XPATH, '//button[.//img[contains(@src,"live_user")]]'),           # broadest
    ]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    @allure.step("Type search query '{query}' and press Enter")
    def type_query(self, query: str) -> "SearchPage":
        """Type *query* into the search input and press Enter to navigate
        to the game category page.
        """
        field = self.wait_for_element_any(self._SEARCH_INPUTS)
        field.clear()
        field.send_keys(query)
        field.send_keys(Keys.RETURN)
        return self

    @allure.step("Click 頻道 (Channels) tab")
    def click_channels_tab(self) -> "SearchPage":
        """Click the 頻道 / Channels tab to filter results to live channels only.

        This tab appears after the search results page loads.
        Selectors will be updated once the real HTML is confirmed.
        """
        self.wait_for_element_any(self._CHANNELS_TAB).click()
        return self

    @allure.step("Scroll channel results down {count} time(s)")
    def scroll_results(self, count: int) -> "SearchPage":
        pause  = self.config.get("twitch", {}).get("scroll_pause_seconds", 1.5)
        pixels = self.config.get("twitch", {}).get("scroll_amount_px", 600)
        for _ in range(count):
            self.scroll_down(pixels)
            time.sleep(pause)
        return self

    @allure.step("Select the streamer at the top of the current screen")
    def select_top_visible_streamer(self) -> None:
        """Click the first streamer card whose top edge is visible in the viewport.

        After scrolling, cards above the fold are off-screen — this picks the
        topmost card actually visible right now, matching the assignment spec:
        'scroll down 2 times → select the streamer at the top of the screen'.
        """
        cards = self._collect_channel_cards()
        if not cards:
            raise RuntimeError(
                "No live streamer cards found. "
                "Twitch DOM may have changed — check _CHANNEL_CARD_SELECTORS."
            )

        top_card = self._top_visible_card(cards)
        # Use click_and_switch_window: Twitch opens streamer pages in a new tab
        self.click_and_switch_window(top_card)

    def results_count(self) -> int:
        """Return the number of visible streamer cards on the page."""
        return len(self._collect_channel_cards())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _collect_channel_cards(self) -> list:
        """Try each selector strategy; return the first non-empty list."""
        for locator in self._CHANNEL_CARD_SELECTORS:
            try:
                elements = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_all_elements_located(locator)
                )
                visible = [e for e in elements if e.is_displayed()]
                if visible:
                    return visible
            except Exception:
                continue
        return []

    def _top_visible_card(self, cards: list):
        """Return the card whose top edge is closest to (and at or below)
        the top of the current viewport.

        Uses getBoundingClientRect().top:
          > 0  → below the viewport top   (visible or below fold)
          < 0  → above the viewport top   (scrolled past / off-screen)

        We pick the card with the smallest non-negative top value — i.e.
        the one sitting right at the top of what the user currently sees.
        """
        candidates = []
        for card in cards:
            top_px = self.driver.execute_script(
                "return arguments[0].getBoundingClientRect().top;", card
            )
            if top_px >= -5:   # -5px tolerance for sub-pixel rounding
                candidates.append((top_px, card))

        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

        # Fallback: all cards are above the fold — return the last one
        # (closest to the bottom of the scrolled-past area).
        return cards[-1]
