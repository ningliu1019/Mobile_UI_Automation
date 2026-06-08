"""test_twitch_wap.py — Twitch WAP test suite.

How to add a new test
---------------------
1. Ask: what do I want to verify?           → shapes the assert
2. Ask: what actions get me there?          → shapes which steps to call
3. Check steps/ and common/ for reuse       → avoid writing page code in tests
4. Add small step/page methods if missing   → keep tests thin
5. Use @allure decorators to label the test → feature / story / title / severity

Run:
    pytest --env=staging -v
    pytest --env=staging -m "smoke"
    pytest --env=staging -m "wap and regression"
"""

import allure
import pytest

from steps.navigation_steps import NavigationSteps
from steps.search_steps import SearchSteps
from steps.streamer_steps import StreamerSteps


@allure.feature("Twitch WAP")
class TestTwitchWAP:

    # ------------------------------------------------------------------
    # Smoke tests  (pytest -m smoke)
    # ------------------------------------------------------------------

    @pytest.mark.wap
    @pytest.mark.smoke
    @allure.story("WAP mode verification")
    @allure.title("Twitch homepage loads in correct mobile (WAP) layout")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_homepage_loads_in_wap_mode(self, driver, config):
        """
        WHAT  — verify the browser is actually in mobile emulator mode
        WHY   — if emulation is broken every other WAP test is meaningless;
                running this as a smoke gate catches config errors early
        HOW   — navigate to Twitch, read viewport dimensions via JS,
                assert width matches the configured device
        """
        nav = NavigationSteps(driver, config)

        # Action
        nav.open_twitch()

        # Assert 1 — correct site
        assert "twitch.tv" in driver.current_url, (
            f"Unexpected URL: {driver.current_url}"
        )

        # Assert 2 — mobile viewport is active
        viewport = nav.verify_wap_mode()

        allure.attach(
            f"width={viewport['width']}  height={viewport['height']}",
            name="viewport_dimensions",
            attachment_type=allure.attachment_type.TEXT,
        )

    @pytest.mark.wap
    @pytest.mark.smoke
    @allure.story("Search and view StarCraft II streamer on mobile")
    @allure.title("Search StarCraft II and open a live streamer page")
    @allure.severity(allure.severity_level.NORMAL)
    def test_search_starcraft_streamer(self, driver, config):
        """
        WHAT  — the 6-step scenario from the assignment spec
        WHY   — core user journey: search → browse → watch
        HOW   — navigate, search, scroll, pick a streamer, dismiss pop-ups,
                wait for the page to settle, take a screenshot
        """
        twitch = config.get("twitch", {})

        # Steps 1–2: navigate to Twitch and open search
        NavigationSteps(driver, config).open_twitch_and_search()

        # Steps 3–5: type query + Enter, scroll 2×, select top visible streamer
        SearchSteps(driver, config).search_scroll_and_pick(
            query=twitch.get("search_query", "StarCraft II"),
            scroll_count=twitch.get("scroll_count", 2),
        )

        # Step 6: dismiss pop-up, wait for load, screenshot
        screenshot_path = StreamerSteps(driver, config).view_and_capture()

        assert screenshot_path, "Screenshot was not saved."

    # ------------------------------------------------------------------
    # Regression tests  (pytest -m regression)
    # ------------------------------------------------------------------

    @pytest.mark.wap
    @pytest.mark.regression
    @allure.story("Search results")
    @allure.title("Searching StarCraft II returns at least one live channel")
    @allure.severity(allure.severity_level.NORMAL)
    def test_search_returns_results(self, driver, config):
        """
        WHAT  — verify search actually surfaces channel cards (not a blank page)
        WHY   — catches broken search API or DOM changes before we even click
        HOW   — navigate, open search, type the query, count visible cards
                (no scroll, no click — we stop right after results appear)

        NOTE  — this test intentionally does NOT click into a streamer.
                It isolates the "search returns results" behaviour so a
                failure here points precisely at the search results layer.
        """
        twitch = config.get("twitch", {})

        NavigationSteps(driver, config).open_twitch_and_search()

        search = SearchSteps(driver, config)
        search.search_for(twitch.get("search_query", "StarCraft II"))

        count = search.get_results_count()

        allure.attach(
            f"Visible channel cards: {count}",
            name="results_count",
            attachment_type=allure.attachment_type.TEXT,
        )

        assert count > 0, (
            f"Expected at least 1 result for '{twitch.get('search_query')}' "
            f"but found none. Twitch DOM may have changed — check _CHANNEL_CARD_SELECTORS."
        )
