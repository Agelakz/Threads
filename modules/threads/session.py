import os
import logging
from typing import Optional
from playwright.sync_api import sync_playwright, BrowserContext, Page

from core.config import config
from core.logger import setup_logger

logger = setup_logger(__name__)

class ThreadsSessionManager:
    """
    Manager for handling Threads.net login, session saving, loading, and validation.
    """
    
    def __init__(self, session_dir: str = "sessions"):
        self.session_dir = session_dir
        self.session_file = os.path.join(session_dir, "threads_session.json")
        self.base_url = "https://www.threads.net"
        
        # Create session directory if it doesn't exist
        if not os.path.exists(self.session_dir):
            os.makedirs(self.session_dir)

    def login(self, headless: bool = False) -> bool:
        """
        Automates the login process for Threads and saves the session.
        headless=False is recommended for first-time login to handle Captcha/2FA manually if needed.
        """
        username = config.THREADS_USERNAME
        password = config.THREADS_PASSWORD
        
        if not username or not password:
            logger.error("Threads credentials are not set in the configuration.")
            return False

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless)
                context = browser.new_context()
                page = context.new_page()
                
                logger.info("Navigating to Threads login page...")
                page.goto(f"{self.base_url}/login")
                
                # Tunggu form login muncul
                page.wait_for_selector('input[type="text"]', timeout=15000)
                
                logger.info("Filling credentials...")
                page.fill('input[type="text"]', username)
                page.fill('input[type="password"]', password)
                
                # Klik tombol login
                page.click('button[type="submit"]')
                
                logger.info("Waiting for login process...")
                
                # Threads sering redirect setelah login sukses. Kita tunggu network idle
                page.wait_for_load_state("networkidle", timeout=15000)
                page.wait_for_timeout(3000) # Buffer animasi
                
                if self._check_is_logged_in(page):
                    logger.info("Login successful. Saving session state...")
                    self.save_session(context)
                    browser.close()
                    return True
                else:
                    logger.warning("Login might have failed or requires manual intervention (Captcha/2FA).")
                    logger.info("Please complete the login manually in the open browser window.")
                    
                    # Jika headless=False, berikan waktu tambahan untuk manual login
                    if not headless:
                        logger.info("Waiting 45 seconds for manual login completion...")
                        page.wait_for_timeout(45000)
                        if self._check_is_logged_in(page):
                            logger.info("Manual login successful. Saving session state...")
                            self.save_session(context)
                            browser.close()
                            return True
                    
                    logger.error("Login failed.")
                    browser.close()
                    return False
                    
        except Exception as e:
            logger.error(f"An error occurred during login: {str(e)}")
            return False

    def save_session(self, context: BrowserContext) -> None:
        """
        Save the browser context's cookies and local storage state.
        """
        context.storage_state(path=self.session_file)
        logger.info(f"Session state saved successfully to {self.session_file}")

    def load_session(self, playwright_instance, headless: bool = True) -> Optional[BrowserContext]:
        """
        Load the saved session state into a new browser context.
        """
        if not os.path.exists(self.session_file):
            logger.warning("Session file does not exist.")
            return None
            
        try:
            browser = playwright_instance.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file)
            logger.info("Session loaded successfully.")
            return context
        except Exception as e:
            logger.error(f"Failed to load session: {str(e)}")
            return None

    def validate_session(self, headless: bool = True) -> bool:
        """
        Check if the saved session is still valid (not expired) by accessing Threads homepage.
        """
        if not os.path.exists(self.session_file):
            logger.info("Cannot validate: No session file found.")
            return False

        try:
            with sync_playwright() as p:
                context = self.load_session(p, headless=headless)
                if not context:
                    return False
                    
                page = context.new_page()
                logger.info("Validating session by navigating to Threads homepage...")
                page.goto(self.base_url)
                
                # Tunggu page load
                page.wait_for_load_state("networkidle", timeout=15000)
                
                is_valid = self._check_is_logged_in(page)
                
                if is_valid:
                    logger.info("Session is valid and active.")
                else:
                    logger.warning("Session is invalid or has expired.")
                
                # Tutup browser setelah selesai divalidasi
                if context and context.browser:
                    context.browser.close()
                return is_valid
                
        except Exception as e:
            logger.error(f"Error during session validation: {str(e)}")
            return False

    def _check_is_logged_in(self, page: Page) -> bool:
        """
        Verify login status by checking DOM elements.
        """
        try:
            # Jika URL masih berada di login page, maka belum login
            if "login" in page.url:
                return False
                
            # Cek apakah form/tombol login ada di layar
            login_buttons = page.locator('a[href*="/login"], button:has-text("Log in")').count()
            if login_buttons > 0:
                return False
                
            return True
        except Exception:
            return False
