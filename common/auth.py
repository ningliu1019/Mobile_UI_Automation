"""auth.py — reusable login and logout actions for Twitch WAP.

Credentials are never hardcoded here.  They come from the environment-
specific config (config/environments/<env>.yaml) and are injected via
.env.<env> files or CI environment variables.

Usage
-----
    from common.auth import AuthActions

    auth = AuthActions(driver, config)
    auth.login()                        # logs in as the default "test_user" account
    auth.login(account_key="mod_user")  # logs in as a different configured account
    auth.logout()
"""

import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from common.modal_handler import ModalHandler
from pages.base_page import BasePage


class AuthActions(BasePage):
    """Login and logout flows for Twitch WAP (mobile web)."""

    # ------------------------------------------------------------------ #
    # Locators                                                             #
    # ------------------------------------------------------------------ #

    # Entry point visible in the nav bar when logged out
    _LOGIN_BUTTON = (By.CSS_SELECTOR, '[data-a-target="login-button"]')

    # Login form fields
    _USERNAME_INPUT = (By.ID, "login-username")
    _PASSWORD_INPUT = (By.ID, "password-input")
    _SUBMIT_BUTTON  = (By.CSS_SELECTOR, '[data-a-target="passport-login-button"]')

    # Login errors / 2FA prompt (for graceful assertions)
    _LOGIN_ERROR    = (By.CSS_SELECTOR, '[data-a-target="passport-login-form"] .error')
    _TWOFA_PROMPT   = (By.CSS_SELECTOR, '[data-a-target="two-factor-submit"]')

    # Logged-in indicators
    _USER_AVATAR    = (By.CSS_SELECTOR, '[data-a-target="user-menu-toggle"]')

    # Logout
    _USER_MENU      = (By.CSS_SELECTOR, '[data-a-target="user-menu-toggle"]')
    _LOGOUT_ITEM    = (By.CSS_SELECTOR, '[data-a-target="logout-button"]')

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    @allure.step("Log in as account '{account_key}'")
    def login(self, account_key: str = "test_user") -> None:
        """Log in using credentials defined under config.accounts.<account_key>.

        Args:
            account_key: Key in config['accounts'] (e.g. 'test_user').
                         Credentials are resolved from environment variables
                         via the config loader — never stored in plain text.
        """
        username, password = self._get_credentials(account_key)

        self._open_login_form()

        username_field = self.wait_for_element(self._USERNAME_INPUT)
        username_field.clear()
        username_field.send_keys(username)

        password_field = self.wait_for_element(self._PASSWORD_INPUT)
        password_field.clear()
        password_field.send_keys(password)

        self.wait_for_element(self._SUBMIT_BUTTON).click()
        self._handle_post_login()

    @allure.step("Log out")
    def logout(self) -> None:
        """Open the user menu and click log out."""
        self.wait_for_element(self._USER_MENU).click()
        self.wait_for_element(self._LOGOUT_ITEM).click()

    @allure.step("Check if user is logged in")
    def is_logged_in(self) -> bool:
        """Return True if the user-avatar / menu toggle is visible."""
        return self.is_present(self._USER_AVATAR, timeout=5)

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _get_credentials(self, account_key: str) -> tuple[str, str]:
        accounts = self.config.get("accounts", {})
        account  = accounts.get(account_key, {})

        username = account.get("username", "")
        password = account.get("password", "")

        if not username or not password:
            raise ValueError(
                f"Credentials for account '{account_key}' are not set. "
                f"Check your .env.<env> file and ensure the matching "
                f"environment variables are exported."
            )
        return username, password

    def _open_login_form(self) -> None:
        """Click the Login button in the nav to open the login form."""
        # Dismiss any overlay that might block the login button first
        ModalHandler(self.driver, self.config).dismiss_cookie_banner()
        self.wait_for_element(self._LOGIN_BUTTON).click()

    def _handle_post_login(self) -> None:
        """Wait for login to complete; raise on visible errors."""
        # Happy path — user avatar appears
        if self.is_present(self._USER_AVATAR, timeout=10):
            return

        # 2-FA prompt — surface a helpful message rather than a timeout
        if self.is_present(self._TWOFA_PROMPT, timeout=3):
            raise NotImplementedError(
                "Two-factor authentication is required for this account. "
                "Disable 2FA on the test account or extend AuthActions to handle it."
            )

        # Generic login error
        if self.is_present(self._LOGIN_ERROR, timeout=3):
            raise RuntimeError(
                "Login failed — check the credentials for this environment."
            )

        raise TimeoutError("Login did not complete within the expected time.")
