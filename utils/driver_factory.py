from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class DriverFactory:
    """Creates and configures a Chrome WebDriver with mobile emulation."""

    @staticmethod
    def create_driver(config: dict) -> webdriver.Chrome:
        options = DriverFactory._build_options(config)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        browser_cfg = config.get("browser", {})
        driver.implicitly_wait(browser_cfg.get("implicit_wait", 10))
        driver.set_page_load_timeout(browser_cfg.get("page_load_timeout", 30))

        return driver

    @staticmethod
    def _build_options(config: dict) -> Options:
        options = Options()

        options.add_experimental_option(
            "mobileEmulation", DriverFactory._mobile_emulation(config)
        )

        browser_cfg = config.get("browser", {})
        if browser_cfg.get("headless", False):
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")

        return options

    @staticmethod
    def _mobile_emulation(config: dict) -> dict:
        device_cfg = config.get("device", {})

        if device_cfg.get("use_named_device", True):
            return {"deviceName": device_cfg.get("name", "iPhone 12 Pro")}

        return {
            "deviceMetrics": {
                "width": device_cfg.get("width", 390),
                "height": device_cfg.get("height", 844),
                "pixelRatio": device_cfg.get("pixel_ratio", 3.0),
            },
            "userAgent": device_cfg.get("user_agent", ""),
        }
