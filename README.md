# Twitch WAP Automation — Mobile Test Framework

End-to-end UI automation suite for Twitch's mobile web (WAP) version, built with **Python · Selenium · pytest · Allure**.

The framework follows the **Page Object Model** with a three-layer architecture (Pages → Steps → Tests) and supports multiple environments out of the box.

---

## Demo

![test-run demo](docs/demo.gif)

---

## Test scenario

| Step | Action |
|------|--------|
| 1 | Navigate to [m.twitch.tv](https://m.twitch.tv) in Chrome mobile emulator (iPhone 12 Pro) |
| 2 | Click the **Browse** button |
| 3 | Type **StarCraft II** and press **Enter** |
| 4 | Click the **頻道 (Channels)** tab to filter to live channels |
| 5 | Scroll down **2 times** |
| 6 | Click the live streamer at the **top of the current screen** |
| 7 | Dismiss any pop-up/modal, wait for the page to load, **take a screenshot** |

---

## Project structure

```
Mobile_automation/
│
├── config/
│   ├── base.yaml                    # Shared: device, browser, test defaults
│   ├── environments/
│   │   ├── staging.yaml             # Staging URL, accounts, timeout overrides
│   │   └── production.yaml          # Production URL, accounts
│   ├── .env.staging.example         # Template — copy to .env.staging, fill in secrets
│   └── .env.production.example      # Template — copy to .env.production, fill in secrets
│
├── pages/                           # LOW LEVEL — locators + raw single-page interactions
│   ├── base_page.py                 # Shared waits, scroll, screenshot utilities
│   ├── home_page.py                 # Twitch homepage locators & actions
│   ├── search_page.py               # Search field, result cards, scroll
│   └── streamer_page.py             # Load detection, screenshot; modals → ModalHandler
│
├── common/                          # CROSS-CUTTING — reused across multiple pages & steps
│   ├── auth.py                      # login(), logout(), is_logged_in()
│   └── modal_handler.py             # dismiss_cookie_banner(), dismiss_mature_content(),
│                                    # dismiss_any() — one place for all overlay selectors
│
├── steps/                           # MID LEVEL — reusable business-action sequences
│   ├── navigation_steps.py          # open_twitch(), open_search(), open_twitch_and_search()
│   ├── search_steps.py              # search_for(), scroll_results(), search_scroll_and_pick()
│   └── streamer_steps.py            # dismiss_popups(), wait_for_load(), view_and_capture()
│
├── tests/                           # HIGH LEVEL — test scenarios that call steps
│   └── test_twitch_wap.py           # 6-step WAP scenario
│
├── utils/
│   ├── config_loader.py             # Merges base + env yaml + .env secrets
│   └── driver_factory.py            # Chrome + mobile emulation wiring
│
├── screenshots/                     # PNG files produced by tests (gitignored)
├── allure-results/                  # Raw Allure data (gitignored)
├── conftest.py                      # Fixtures, --env flag, failure-screenshot hook
├── pytest.ini                       # Allure output dir + custom markers
└── requirements.txt
```

### Four-layer design

```
Tests        → call Steps          (what the test does, in plain English)
Steps        → call Pages/Common   (reusable action sequences, shared across tests)
Common       → called by any layer (cross-cutting: auth, modals — not page-specific)
Pages        → call Driver         (single source of truth for locators)
```

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.9+ |
| Google Chrome | Latest stable |
| Allure CLI (optional, for HTML report) | 2.x |

---

## Setup

```bash
# 1 — clone / enter the repo
git clone <your-repo-url>
cd Mobile_automation

# 2 — create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3 — install dependencies
pip install -r requirements.txt
```

ChromeDriver is managed automatically by `webdriver-manager` — no manual installation needed.

---

## Environment configuration

Config is split into three layers that are merged at runtime:

| File | Purpose | In Git? |
|------|---------|---------|
| `config/base.yaml` | Device, browser, shared test defaults | ✅ Yes |
| `config/environments/<env>.yaml` | URLs, timeouts, account key names | ✅ Yes |
| `config/.env.<env>` | Actual credentials / secrets | ❌ **No** (gitignored) |

### Setting up credentials

```bash
# Staging
cp config/.env.staging.example config/.env.staging
# Edit .env.staging and fill in real values

# Production
cp config/.env.production.example config/.env.production
# Edit .env.production and fill in real values
```

The loader substitutes `${VAR_NAME}` placeholders in the YAML files with the
matching environment variable. Variables already present in the OS environment
(e.g. CI/CD secrets) always take priority over `.env` files.

### Changing the emulated device

Edit `config/base.yaml`:

```yaml
device:
  use_named_device: true
  name: "iPhone 12 Pro"   # any Chrome DevTools device name
```

Other options: `"Pixel 7"`, `"Samsung Galaxy S20 Ultra"`, etc.
Set `use_named_device: false` to supply custom `width` / `height` / `pixel_ratio` / `user_agent`.

---

## Running the tests

```bash
# Run against staging (default)
pytest

# Run against production
pytest --env=production

# Run only WAP smoke tests on staging
pytest --env=staging -m "wap and smoke"

# Headless mode for CI (override in base.yaml or pass env var)
HEADLESS=true pytest --env=staging
```

---

## Viewing the Allure report

```bash
# Install Allure CLI once (macOS)
brew install allure

# Serve the report in your browser
allure serve allure-results
```

The report includes per-step details, the final screenshot, and an automatic failure screenshot if a test fails.

---

## Extending the framework

| What to add | Where |
|-------------|-------|
| New page | `pages/<name>_page.py` inheriting `BasePage` |
| New cross-cutting action (auth, modals, cookies …) | `common/<concern>.py` inheriting `BasePage` |
| New reusable flow | `steps/<area>_steps.py` — orchestrates pages + common |
| New test | `tests/test_<feature>.py` — import and call step classes |
| New environment | `config/environments/<env>.yaml` + `.env.<env>.example`, add to `SUPPORTED_ENVS` in `config_loader.py` |
| New account type | Add a key under `accounts:` in the relevant `environments/*.yaml` |
| New device | `config/base.yaml` → change `device.name` |
| New marker | `pytest.ini` → `markers` section |
