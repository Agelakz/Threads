import time
import logging
from typing import List, Dict
from playwright.sync_api import sync_playwright

from modules.threads.session import ThreadsSessionManager
from database.db import SessionLocal, init_db
from database.models import ThreadPost

logger = logging.getLogger(__name__)

class ThreadsMonitor:
    """
    Monitor platform Threads untuk mencari post berdasarkan keyword,
    melakukan parsing data, dan menyimpannya ke database MVP (SQLite).
    """
    def __init__(self):
        self.session_manager = ThreadsSessionManager()
        self.base_url = "https://www.threads.net"
        
        # Inisialisasi skema database jika belum dibuat
        init_db()

    def search_and_collect(self, keyword: str, limit: int = 10, headless: bool = True) -> List[Dict]:
        """
        Mencari keyword di Threads, melakukan scroll otomatis, mem-parse hasil post,
        dan langsung menyimpannya ke dalam database.
        """
        logger.info(f"Mulai monitoring Threads untuk keyword: '{keyword}'")
        
        # 1. Pastikan session valid menggunakan Session Manager (Module 1)
        if not self.session_manager.validate_session(headless=headless):
            logger.error("Session tidak valid. Harap jalankan script login terlebih dahulu.")
            return []

        posts_collected = []
        
        try:
            with sync_playwright() as p:
                context = self.session_manager.load_session(p, headless=headless)
                if not context:
                    return []
                    
                page = context.new_page()
                
                # Mengubah spasi menjadi + untuk URL query
                search_url = f"{self.base_url}/search?q={keyword.replace(' ', '+')}"
                logger.info(f"Membuka halaman pencarian: {search_url}")
                page.goto(search_url)
                
                # Tunggu proses loading render Javascript
                page.wait_for_load_state("networkidle", timeout=20000)
                page.wait_for_timeout(3000) # Buffer untuk animasi DOM Threads
                
                # Auto-scroll untuk memicu lazy loading sehingga lebih banyak post yang ter-render
                logger.info("Scrolling layar untuk memuat hasil post...")
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)
                
                # 2. Collect & Parse Post
                logger.info("Parsing data hasil pencarian...")
                
                # Mengekstrak DOM menggunakan eksekusi script JS
                js_extract_code = """
                () => {
                    const posts = [];
                    // Mencari seluruh elemen A (link) yang mengarah spesifik ke halaman /post/
                    const postLinks = document.querySelectorAll('a[href*="/post/"]');
                    const seenUrls = new Set();
                    
                    postLinks.forEach(link => {
                        const url = link.href;
                        // Hindari duplikasi parsing dari link yang sama
                        if(seenUrls.has(url)) return;
                        seenUrls.add(url);
                        
                        // Ekstrak author dan post_id dari URL Threads (/ @username / post / Cxxxxxx)
                        const urlObj = new URL(url);
                        const pathParts = urlObj.pathname.split('/');
                        let author = "";
                        let postId = "";
                        
                        if(pathParts.length >= 4) {
                            author = pathParts[1].replace('@', '');
                            postId = pathParts[3];
                        }
                        
                        // Naik hirarki DOM ke atas untuk membidik kontainer utama pembungkus Post
                        let container = link;
                        for(let i=0; i<6; i++) {
                            if(container.parentElement) {
                                container = container.parentElement;
                            }
                        }
                        
                        posts.push({
                            post_id: postId,
                            author_username: author,
                            url: url,
                            content: container.innerText
                        });
                    });
                    return posts;
                }
                """
                
                raw_posts = page.evaluate(js_extract_code)
                logger.info(f"Ditemukan {len(raw_posts)} kandidat post di DOM layar.")
                
                # 3. Validasi & Simpan ke Database
                for rp in raw_posts:
                    if len(posts_collected) >= limit:
                        break
                        
                    # Filter data yang tidak memiliki id atau isi konten
                    if not rp.get("post_id") or not rp.get("content"):
                        continue
                        
                    content = rp["content"].strip()
                    
                    post_data = {
                        "post_id": rp["post_id"],
                        "author_username": rp["author_username"],
                        "url": rp["url"],
                        "content": content,
                        "keyword": keyword
                    }
                    
                    posts_collected.append(post_data)
                    self._save_to_db(post_data)

                logger.info(f"Proses selesai. Berhasil mengumpulkan & menyimpan {len(posts_collected)} post.")
                context.browser.close()
                return posts_collected
                
        except Exception as e:
            logger.error(f"Error pada ThreadsMonitor: {e}")
            return posts_collected

    def _save_to_db(self, data: Dict):
        """
        Menyimpan data hasil parsing secara langsung ke database SQLite (SQLAlchemy).
        Hanya menyimpan jika ID Post belum terekam untuk mencegah data kembar.
        """
        db = SessionLocal()
        try:
            # Cek duplikasi
            existing = db.query(ThreadPost).filter(ThreadPost.post_id == data["post_id"]).first()
            if not existing:
                new_post = ThreadPost(
                    post_id=data["post_id"],
                    author_username=data["author_username"],
                    content=data["content"],
                    url=data["url"],
                    keyword=data["keyword"]
                )
                db.add(new_post)
                db.commit()
                logger.debug(f"-> [DB] Post {data['post_id']} berhasil disimpan.")
            else:
                logger.debug(f"-> [DB] Post {data['post_id']} diabaikan (sudah pernah di-scrape).")
        except Exception as e:
            db.rollback()
            logger.error(f"Gagal menyimpan ke database: {e}")
        finally:
            db.close()
