import os
import logging
from typing import Optional
from playwright.sync_api import sync_playwright, BrowserContext, Page

from core.config import config
from core.logger import setup_logger

logger = setup_logger(__name__)

class ShopeeSessionManager:
    """
    Manager for handling Shopee Affiliate login, session saving, loading, and validation.
    """
    
    def __init__(self, session_dir: str = "sessions"):
        self.session_dir = session_dir
        self.session_file = os.path.join(session_dir, "shopee_session.json")
        self.base_url = "https://affiliate.shopee.co.id"
        
        # Create session directory if it doesn't exist
        if not os.path.exists(self.session_dir):
            os.makedirs(self.session_dir)

    def login(self, headless: bool = False) -> bool:
        """
        Automates or assists the login process for Shopee Affiliate and saves the session.
        Since Shopee frequently requires SMS OTP or QR Code scan, headless=False is strongly recommended
        for the initial login.
        """
        username = config.SHOPEE_AFFILIATE_USERNAME
        password = config.SHOPEE_AFFILIATE_PASSWORD
        
        if not username or not password:
            logger.error("Shopee credentials are not set in the configuration.")
            return False

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless)
                context = browser.new_context()
                page = context.new_page()
                
                logger.info("Navigating to Shopee Affiliate login page...")
                page.goto(f"{self.base_url}/login")
                
                # Coba auto-fill jika memungkinkan (form Shopee kadang dinamis)
                try:
                    page.wait_for_selector('input[name="loginKey"]', timeout=10000)
                    logger.info("Filling credentials...")
                    page.fill('input[name="loginKey"]', username)
                    page.fill('input[name="password"]', password)
                    # Tekan Enter untuk login
                    page.press('input[name="password"]', 'Enter')
                except Exception:
                    logger.warning("Could not auto-fill Shopee login form. Manual intervention required.")
                
                logger.info("Waiting for login process (Requires manual OTP/Captcha handling)...")
                
                # Berikan waktu yang cukup panjang untuk user menyelesaikan verifikasi OTP (SMS/WA)
                # atau scan QR code secara manual
                if not headless:
                    logger.info("Waiting 60 seconds for manual login completion (OTP/QR/Captcha)...")
                    page.wait_for_timeout(60000)
                else:
                    page.wait_for_load_state("networkidle", timeout=15000)
                
                if self._check_is_logged_in(page):
                    logger.info("Shopee Login successful. Saving session state...")
                    self.save_session(context)
                    browser.close()
                    return True
                else:
                    logger.error("Shopee Login failed. Check credentials, Captcha, or OTP.")
                    browser.close()
                    return False
                    
        except Exception as e:
            logger.error(f"An error occurred during Shopee login: {str(e)}")
            return False

    def save_session(self, context: BrowserContext) -> None:
        """
        Save the browser context's cookies and local storage state.
        """
        context.storage_state(path=self.session_file)
        logger.info(f"Shopee Session state saved successfully to {self.session_file}")

    def load_session(self, playwright_instance, headless: bool = True) -> Optional[BrowserContext]:
        """
        Load the saved session state into a new browser context.
        """
        if not os.path.exists(self.session_file):
            logger.warning("Shopee Session file does not exist.")
            return None
            
        try:
            browser = playwright_instance.chromium.launch(headless=headless)
            context = browser.new_context(storage_state=self.session_file)
            logger.info("Shopee Session loaded successfully.")
            return context
        except Exception as e:
            logger.error(f"Failed to load Shopee session: {str(e)}")
            return None

    def validate_session(self, headless: bool = True) -> bool:
        """
        Check if the saved session is still valid (not expired) by accessing the Affiliate dashboard.
        """
        if not os.path.exists(self.session_file):
            logger.info("Cannot validate: No Shopee session file found.")
            return False

        try:
            with sync_playwright() as p:
                context = self.load_session(p, headless=headless)
                if not context:
                    return False
                    
                page = context.new_page()
                logger.info("Validating Shopee session by navigating to Affiliate dashboard...")
                page.goto(self.base_url)
                
                page.wait_for_load_state("networkidle", timeout=15000)
                page.wait_for_timeout(3000) # Buffer for redirect
                
                is_valid = self._check_is_logged_in(page)
                
                if is_valid:
                    logger.info("Shopee Session is valid and active.")
                else:
                    logger.warning("Shopee Session is invalid or has expired.")
                
                if context and context.browser:
                    context.browser.close()
                return is_valid
                
        except Exception as e:
            logger.error(f"Error during Shopee session validation: {str(e)}")
            return False

    def _check_is_logged_in(self, page: Page) -> bool:
        """
        Verify login status by checking URL redirection and DOM elements.
        """
        try:
            # Biasanya Shopee me-redirect kembali ke halaman login jika session mati
            if "login" in page.url.lower():
                return False
                
            # Cek form login
            login_buttons = page.locator('a[href*="/login"], button:has-text("Log in"), button:has-text("Log In")').count()
            if login_buttons > 0:
                return False
                
            # Jika berhasil masuk ke dashboard (biasanya URL tidak mengandung login dan tidak ada form login)
            return True
        except Exception:
            return False
