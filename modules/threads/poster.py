import time
import logging
from playwright.sync_api import sync_playwright

from modules.threads.session import ThreadsSessionManager
from database.db import SessionLocal
from database.models import ThreadPost

logger = logging.getLogger(__name__)

class ThreadsPoster:
    """
    Modul untuk memposting balasan (reply_draft) secara otomatis ke Threads
    berdasarkan data post yang sudah disetujui (is_processed = True).
    """

    def __init__(self):
        self.session_manager = ThreadsSessionManager()
        
    def post_all_approved(self, headless=False):
        """
        Mencari semua post yang sudah diproses dan mengirimkan balasannya.
        """
        db = SessionLocal()
        try:
            # Ambil post yang siap diposting (status = APPROVED)
            approved_posts = db.query(ThreadPost).filter(
                ThreadPost.status == "APPROVED",
                ThreadPost.reply_draft != None,
                ThreadPost.reply_draft != ""
            ).all()

            if not approved_posts:
                logger.info("Tidak ada draft balasan yang perlu dikirim ke Threads.")
                return 0

            logger.info(f"Menemukan {len(approved_posts)} balasan untuk dikirim.")
            success_count = 0

            with sync_playwright() as p:
                context = self.session_manager.load_session(p, headless=headless)
                if not context:
                    logger.error("Session Threads tidak valid. Tidak dapat memposting.")
                    return 0

                try:
                    from main import _update_status
                    for post in approved_posts:
                        if self._post_reply(context, post):
                            success_count += 1
                            _update_status(post.post_id, "SENT", "Auto-reply sukses")
                            # Beri jeda antar post untuk menghindari spam detection
                            time.sleep(5)
                        else:
                            _update_status(post.post_id, "FAILED", "Auto-reply gagal")
                finally:
                    if context.browser:
                        context.browser.close()

            return success_count

        finally:
            db.close()

    def _post_reply(self, context, post: ThreadPost) -> bool:
        """
        Melakukan navigasi ke URL thread spesifik dan memasukkan teks balasan.
        """
        page = context.new_page()
        try:
            logger.info(f"Menavigasi ke post: {post.url}")
            page.goto(post.url)
            page.wait_for_load_state("networkidle", timeout=15000)

            # Cari input box untuk reply. 
            # Threads menggunakan div dengan contenteditable="true" atau placeholder "Reply..."
            reply_selectors = [
                'div[contenteditable="true"][aria-label*="Reply"]',
                'div[contenteditable="true"][aria-label*="Balas"]',
                'div[data-lexical-editor="true"]'
            ]
            
            input_box = None
            for selector in reply_selectors:
                if page.locator(selector).count() > 0:
                    input_box = page.locator(selector).first
                    break
            
            if not input_box:
                logger.warning(f"Tidak dapat menemukan kolom input balasan di post {post.id}")
                return False

            # Fokus dan ketik draft
            input_box.click()
            page.wait_for_timeout(500) # Jeda manusiawi
            
            # Ketik per karakter agar lebih natural
            input_box.type(post.reply_draft, delay=30)
            
            # Cari tombol Post/Kirim
            post_button_selectors = [
                'div[role="button"]:has-text("Post")',
                'div[role="button"]:has-text("Posting")'
            ]
            
            post_button = None
            for selector in post_button_selectors:
                if page.locator(selector).count() > 0:
                    post_button = page.locator(selector).first
                    break
                    
            if not post_button:
                logger.warning("Kolom input ditemukan, tetapi tombol 'Post' tidak ditemukan.")
                return False

            # Klik tombol post
            post_button.click()
            
            # Tunggu respon bahwa posting berhasil (contoh: muncul toast atau input box clear)
            page.wait_for_timeout(3000)
            logger.info(f"Berhasil mengirim balasan ke {post.author_username}")
            return True

        except Exception as e:
            logger.error(f"Gagal mengirim balasan ke {post.url}: {e}")
            return False
        finally:
            page.close()
