import os

import allure
import pytest

from utils.config_loader import SUPPORTED_ENVS, load_config


# ---------------------------------------------------------------------------
# CLI option
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default="staging",
        choices=SUPPORTED_ENVS,
        help=f"Target environment. One of {SUPPORTED_ENVS}. Default: staging",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def env(request) -> str:
    """The environment name selected via --env."""
    return request.config.getoption("--env")


@pytest.fixture(scope="session")
def config(env) -> dict:
    """Fully-resolved config: base.yaml ⊕ environments/<env>.yaml ⊕ .env.<env>."""
    return load_config(env)


@pytest.fixture(scope="session")
def accounts(config) -> dict:
    """Convenience shortcut to config['accounts'].

    Usage in a test or step:
        def test_something(accounts):
            user = accounts["test_user"]
            # user["username"], user["password"]
    """
    return config.get("accounts", {})


@pytest.fixture(scope="function")
def driver(config):
    """Mobile-emulated Chrome WebDriver; created and quit per test function."""
    from utils.driver_factory import DriverFactory

    _driver = DriverFactory.create_driver(config)
    yield _driver
    _driver.quit()


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """Ensure output directories exist before any test runs."""
    os.makedirs("screenshots", exist_ok=True)
    os.makedirs("allure-results", exist_ok=True)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Attach a failure screenshot to the Allure report automatically."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        _driver = item.funcargs.get("driver")
        if _driver:
            try:
                allure.attach(
                    _driver.get_screenshot_as_png(),
                    name="failure_screenshot",
                    attachment_type=allure.attachment_type.PNG,
                )
            except Exception:
                pass
