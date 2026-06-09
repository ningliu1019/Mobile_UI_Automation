import allure
import pytest

from steps.navigation_steps import NavigationSteps
from steps.search_steps import SearchSteps
from steps.streamer_steps import StreamerSteps


@allure.feature("Twitch WAP")
class TestTwitchWAP:

    @pytest.mark.wap
    @pytest.mark.smoke
    @allure.story("Search and open a StarCraft II streamer on mobile")
    @allure.title("Search StarCraft II and open a streamer's channel page")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_search_starcraft_streamer(self, driver, config):
        """
        WHAT  — the full 6-step scenario from the assignment spec
        WHY   — core user journey: open Twitch → search → browse → open a streamer
        HOW   — go to Twitch, open search, input StarCraft II, scroll 2×,
                select one streamer, then wait for the streamer page to load
                and take a screenshot

        Assignment steps
            1. go to Twitch
            2. click the search icon
            3. input "StarCraft II"
            4. scroll down 2 times
            5. select one streamer
            6. on the streamer page, wait until loaded and take a screenshot

        We open a LIVE streamer and verify the player actually loads and plays
        (the <video> playhead advances) with no decode error, then screenshot.
        """
        twitch = config.get("twitch", {})

        # Steps 1–3: go to Twitch, open search, input the query
        NavigationSteps(driver, config).open_twitch_and_search()

        # Steps 4–5: scroll 2×, then select one (live) streamer
        channel = SearchSteps(driver, config).search_scroll_and_pick(
            query=twitch.get("search_query", "StarCraft II"),
            scroll_count=twitch.get("scroll_count", 2),
        )

        # Step 6: wait for the player to load/play, then take a screenshot
        status = StreamerSteps(driver, config).view_and_verify()

        allure.attach(
            "\n".join(f"{k}={v}" for k, v in status.items()) + f"\nchannel={channel}",
            name="streamer_status",
            attachment_type=allure.attachment_type.TEXT,
        )

        # Reached the selected streamer page, player loaded, screenshot saved.
        assert status["screenshot"], "Screenshot was not saved."
        assert channel and channel.lower() in status["url"].lower(), (
            f"Did not land on the selected channel. "
            f"channel={channel!r} url={status['url']!r}"
        )
        assert status["player_present"], (
            f"Streamer page did not load a video player. url={status['url']!r}. "
            f"Twitch DOM may have changed — check StreamerPage._LOAD_INDICATORS."
        )
        # The player must actually play (and not be sitting on a decode error).
        assert status["player_error"] == "", (
            f"Player decode error {status['player_error']!r} on the streamer page."
        )
        assert status["video_playing"], (
            f"Player did not play — the <video> playhead did not advance. "
            f"player_error={status['player_error']!r}, url={status['url']!r}"
        )
