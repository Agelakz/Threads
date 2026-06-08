import time
import logging
import urllib.parse
from typing import List, Dict
from playwright.sync_api import sync_playwright

from modules.shopee.session import ShopeeSessionManager

logger = logging.getLogger(__name__)

class ShopeeProductFinder:
    """
    Module untuk mencari produk di Shopee berdasarkan keyword,
    serta mengambil detail dasar seperti nama produk, harga, dan URL.
    """
    
    def __init__(self):
        # Sesuai aturan: Gunakan session Shopee yang sudah dibuat sebelumnya.
        self.session_manager = ShopeeSessionManager()
        
        # URL utama untuk pencarian barang
        self.base_url = "https://shopee.co.id"

    def search_products(self, keyword: str, limit: int = 5, headless: bool = True) -> List[Dict]:
        """
        Mencari produk di Shopee dan mengembalikan daftar dictionary berisi
        nama, harga, dan url.
        """
        logger.info(f"Mencari produk Shopee dengan keyword: '{keyword}'")
        
        products = []
        
        for attempt in range(1, 4):
            try:
                with sync_playwright() as p:
                    # Me-load session affiliate jika tersedia agar request dikenali
                    # sebagai akun pengguna terdaftar (mencegah anti-bot agresif Shopee)
                    context = self.session_manager.load_session(p, headless=headless)
                    
                    # Fallback ke context anonim jika gagal load session (agar pencarian tetap jalan)
                    if not context:
                        logger.warning("Session Shopee tidak ditemukan. Melanjutkan pencarian sebagai Guest.")
                        browser = p.chromium.launch(headless=headless)
                        context = browser.new_context()
                    else:
                        browser = context.browser
                    
                    page = context.new_page()
                    
                    # Menuju halaman pencarian Shopee dengan URL Encode standar
                    query_string = urllib.parse.urlencode({'keyword': keyword})
                    search_url = f"{self.base_url}/search?{query_string}"
                    logger.info(f"Membuka halaman pencarian: {search_url}")
                    page.goto(search_url)
                    
                    # Tunggu agar kerangka website termuat sepenuhnya
                    page.wait_for_load_state("networkidle", timeout=20000)
                    page.wait_for_timeout(4000) # Buffer khusus render client-side react Shopee
                    
                    for _ in range(4):
                        page.evaluate("window.scrollBy(0, window.innerHeight);")
                        page.wait_for_timeout(1500)
                    
                    logger.info("Parsing data produk dari DOM...")
                    
                    # Injeksi Javascript untuk mem-parsing kartu produk.
                    # Kita mencari nama (teks panjang) dan harga (mengandung string Rp)
                    js_extract_code = """
                    () => {
                        const items = [];
                        // Shopee membungkus kartu produk dengan link <a> yang menuju produk
                        const cards = document.querySelectorAll('a[data-sqe="link"]');
                        
                        if (cards.length > 0) {
                            cards.forEach(card => {
                                let url = card.href;
                                let name = "";
                                let price = "";
                                
                                const textElements = card.querySelectorAll('span, div');
                                textElements.forEach(el => {
                                    const text = el.innerText.trim();
                                    if (text.includes('Rp')) {
                                        price = text.replace(/\\n/g, ' ');
                                    } else if (text.length > 15 && !text.includes('Terjual') && !text.includes('Diskon')) {
                                        // Asumsi text terpanjang pertama adalah judul
                                        if(name === "") name = text.replace(/\\n/g, ' ');
                                    }
                                });
                                
                                if (url && name && price) {
                                    items.push({name, price, url});
                                }
                            });
                            return items;
                        }
                        
                        // Fallback jika class/data attribute berubah (Shopee sering update DOM)
                        const fallbackCards = document.querySelectorAll('div.col-xs-2-4');
                        fallbackCards.forEach(card => {
                            const linkEl = card.querySelector('a');
                            if(!linkEl) return;
                            
                            let url = linkEl.href;
                            let name = "";
                            let price = "";
                            
                            const textElements = card.querySelectorAll('div, span');
                            textElements.forEach(el => {
                                const text = el.innerText.trim();
                                if (text.includes('Rp')) {
                                    price = text.replace(/\\n/g, ' ');
                                } else if (text.length > 15 && !text.includes('Terjual') && !text.includes('KAB.')) {
                                    if(name === "") name = text.replace(/\\n/g, ' ');
                                }
                            });
                            
                            if (url && name && price) {
                                items.push({name, price, url});
                            }
                        });
                        
                        return items;
                    }
                    """
                    
                    raw_products = page.evaluate(js_extract_code)
                    logger.info(f"Ditemukan {len(raw_products)} kandidat produk di layar.")
                    
                    # Filter, batasi jumlah, dan bersihkan URL dari tracking tag yang berlebihan
                    seen_urls = set()
                    for rp in raw_products:
                        if len(products) >= limit:
                            break
                            
                        # Bersihkan query parameter tracker (?sp_atk=...) untuk mendapatkan link produk murni
                        clean_url = rp['url'].split('?')[0]
                        
                        if clean_url in seen_urls:
                            continue
                            
                        seen_urls.add(clean_url)
                        
                        products.append({
                            "name": rp["name"].strip(),
                            "price": rp["price"].strip(),
                            "url": clean_url
                        })
                    
                    logger.info(f"Berhasil mengamankan {len(products)} produk final.")
                    return products
                    
            except Exception as e:
                logger.error(f"Error pada ShopeeProductFinder (Percobaan {attempt}/3): {e}")
                if attempt == 3:
                    logger.error("Gagal melakukan pencarian produk Shopee setelah 3 kali percobaan.")
                else:
                    time.sleep(2 ** attempt)
        
        return products
