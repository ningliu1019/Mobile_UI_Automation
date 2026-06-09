import time

import allure
from selenium.common.exceptions import (
    InvalidSelectorException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage


class SearchPage(BasePage):
    """Twitch search / browse page (mobile WAP — m.twitch.tv/directory).

    Confirmed flow from DevTools Recorder (2025-06-08):
      1. After clicking Browse the search input is inside #twilight-sticky-header-root
      2. Type query then press Enter → navigates to the search results page
      3. Live streamer cards are <article> > <button> with an
         <img src="live_user_*"> thumbnail.
      4. After scrolling, "select one streamer" means the card at the TOP of the
         current viewport (see select_top_visible_streamer).
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
        """Click the 頻道 / Channels tab to filter results to channels.

        The channels list contains both live and offline channels; it appears
        after the search results page loads.
        """
        self.wait_for_element_any(self._CHANNELS_TAB).click()
        return self

    @allure.step("Scroll channel results down {count} time(s)")
    def scroll_results(self, count: int) -> "SearchPage":
        # Wait for at least one card to be present before scrolling.
        # If we scroll while Twitch is still rendering the channel list, the
        # SPA can reset the scroll position when the new DOM nodes attach —
        # making the scroll appear to have never happened.
        self._collect_channel_cards()

        pause  = self.config.get("twitch", {}).get("scroll_pause_seconds", 1.5)
        pixels = self.config.get("twitch", {}).get("scroll_amount_px", 600)
        for _ in range(count):
            self.scroll_down(pixels)
            time.sleep(pause)
        return self

    @allure.step("Select the streamer at the top of the current screen")
    def select_top_visible_streamer(self) -> str:
        """Open the live streamer at the top of the viewport and return its name.

        Matches the assignment spec ("scroll down 2 times → select one
        streamer"): picks the topmost live card currently visible, then
        navigates directly to the channel URL on the configured MOBILE host.

        driver.get() is used instead of a tap: a raw click triggers Twitch's
        twitch:// deep-link via window.open(), which fires the OS protocol
        handler and can crash the tab. Building the URL on m.twitch.tv (not
        www) avoids the www→m ``?desktop-redirect=true`` bounce, which combined
        with the page's hard refresh would drop the player into a #3000 state.
        """
        cards = self._collect_channel_cards()
        if not cards:
            raise RuntimeError(
                "No live streamer cards found. "
                "Twitch DOM may have changed — check _CHANNEL_CARD_SELECTORS."
            )
        name = self._channel_name_for_card(self._top_visible_card(cards))
        if not name:
            raise RuntimeError(
                "Could not extract a channel name from the selected card."
            )
        base = self.config.get("twitch", {}).get("url", "https://m.twitch.tv").rstrip("/")
        self.driver.get(f"{base}/{name}")
        return name

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
            # TimeoutException: selector matched nothing in time.
            # InvalidSelectorException: a `:has()` selector this browser build
            # doesn't support.
            # StaleElementReferenceException: the SPA re-rendered between match
            # and the is_displayed() check.
            # Fall through to the next strategy in every case.
            except (TimeoutException, InvalidSelectorException,
                    StaleElementReferenceException):
                continue
        return []

    def _channel_name_for_card(self, card) -> str:
        """Extract the channel login name for a live card, or '' if not found.

        The live preview thumbnail's src always carries the channel name
        (live_user_<name>-WxH.jpg); falls back to an <a href> ancestor.
        """
        return self.driver.execute_script(r"""
            var el = arguments[0];
            var article = el.closest('article') || el;
            var img = article.querySelector('img[src*="live_user"]');
            if (img) {
                var m = img.src.match(/live_user_([^\-\/]+)/);
                if (m && m[1]) return m[1];
            }
            var a = article.querySelector('a[href*="twitch.tv/"]') || el.closest('a[href]');
            if (a) {
                var href = a.getAttribute('href') || '';
                var mm = href.match(/twitch\.tv\/([^\/?#]+)/i) || href.match(/^\/([^\/?#]+)/);
                if (mm && mm[1]) return mm[1];
            }
            return '';
        """, card) or ""

    def _top_visible_card(self, cards: list):
        """Return the card whose top edge is closest to (and at or below) the
        top of the current viewport — the one the user sees at the top now.

        getBoundingClientRect().top: > 0 below the fold, < 0 scrolled past. We
        pick the smallest non-negative top; if all are above the fold, the last.
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
        return cards[-1]
