import logging
from typing import Optional
from playwright.sync_api import sync_playwright

from modules.shopee.session import ShopeeSessionManager
from database.db import SessionLocal, init_db
from database.models import AffiliateLink

logger = logging.getLogger(__name__)

class ShopeeLinkGenerator:
    """
    Module untuk mengonversi URL produk Shopee biasa menjadi URL Affiliate (Custom Link)
    menggunakan dashboard Shopee Affiliate.
    """
    
    def __init__(self):
        self.session_manager = ShopeeSessionManager()
        # Endpoint form Custom Link Shopee Affiliate
        self.custom_link_url = "https://affiliate.shopee.co.id/offer/custom_link"
        
        # Pastikan tabel baru (AffiliateLink) di-create jika belum ada
        init_db()

    def generate_affiliate_link(self, product_url: str, headless: bool = True) -> Optional[str]:
        """
        Menerima URL produk, men-generate link affiliate (shp.ee), dan menyimpannya ke database.
        Jika link produk tersebut sudah pernah di-generate (ada di DB), langsung ambil dari DB.
        """
        # 1. Cek di Database terlebih dahulu agar tidak redundant
        db = SessionLocal()
        try:
            existing_link = db.query(AffiliateLink).filter(AffiliateLink.original_url == product_url).first()
            if existing_link and existing_link.affiliate_url:
                logger.info("Link affiliate ditemukan di Database (Cache Hit).")
                return existing_link.affiliate_url
        except Exception as e:
            logger.error(f"Error mengakses database: {e}")
        finally:
            db.close()

        # 2. Proses pembuatan link via Browser Automation
        logger.info("Mulai generate affiliate link via Shopee Dashboard...")
        if not self.session_manager.validate_session(headless=headless):
            logger.error("Session Shopee tidak valid. Harap login affiliate terlebih dahulu.")
            return None

        affiliate_url = None
        try:
            with sync_playwright() as p:
                context = self.session_manager.load_session(p, headless=headless)
                if not context:
                    return None
                    
                browser = context.browser
                page = context.new_page()
                page.goto(self.custom_link_url)
                
                # Tunggu form dashboard render sepenuhnya
                page.wait_for_load_state("networkidle", timeout=20000)
                page.wait_for_timeout(3000)
                
                # Cari textarea atau input text yang berfungsi untuk menerima URL produk
                # Shopee Affiliate UI sering berupa textarea atau input ber-placeholder spesifik
                input_selector = 'textarea, input[placeholder*="http"], input[placeholder*="URL"]'
                page.wait_for_selector(input_selector, timeout=15000)
                
                logger.info("Memasukkan URL produk ke kolom Custom Link...")
                input_el = page.locator(input_selector).first
                input_el.fill(product_url)
                
                # Klik tombol "Dapatkan Tautan" atau "Get Link"
                # Kita gunakan locator yang luwes berdasarkan teks tombol lazim di UI Shopee Affiliate
                button_selector = 'button:has-text("Dapatkan Tautan"), button:has-text("Get Link")'
                page.locator(button_selector).first.click()
                
                # Tunggu proses background generator Shopee (biasanya sebentar)
                page.wait_for_timeout(4000)
                
                logger.info("Mengambil hasil URL affiliate (shp.ee)...")
                
                # Ekstrak hasil URL affiliate dari layar. Biasanya berbentuk input readonly
                # atau teks link "https://shp.ee/xxx" atau "https://shope.ee/xxx"
                js_extract_link = """
                () => {
                    // Cari dalam kotak input
                    const inputs = document.querySelectorAll('input');
                    for (let input of inputs) {
                        if (input.value.includes('shp.ee') || input.value.includes('shope.ee')) {
                            return input.value;
                        }
                    }
                    
                    // Fallback: Cari text di dalam span/div jika formatnya berupa label
                    const textElements = document.querySelectorAll('span, div');
                    for (let el of textElements) {
                        if (el.innerText.includes('shp.ee') || el.innerText.includes('shope.ee')) {
                            return el.innerText.trim();
                        }
                    }
                    return null;
                }
                """
                
                affiliate_url = page.evaluate(js_extract_link)
                
                if affiliate_url:
                    logger.info(f"Berhasil! Affiliate link: {affiliate_url}")
                    # 3. Simpan ke database
                    self._save_to_db(product_url, affiliate_url)
                else:
                    logger.warning("Gagal mengekstrak text affiliate link dari antarmuka web.")
                
                browser.close()
                return affiliate_url
                
        except Exception as e:
            logger.error(f"Terjadi kesalahan saat generate link: {e}")
            return None

    def _save_to_db(self, original_url: str, affiliate_url: str):
        """Menyimpan record original url dan affiliate url ke dalam database."""
        db = SessionLocal()
        try:
            new_record = AffiliateLink(original_url=original_url, affiliate_url=affiliate_url)
            db.add(new_record)
            db.commit()
            logger.debug(f"-> [DB] Affiliate link disimpan ke database SQLite.")
        except Exception as e:
            db.rollback()
            logger.error(f"Gagal menyimpan ke database (Mungkin redundan): {e}")
        finally:
            db.close()
