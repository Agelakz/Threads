import time
import logging
import google.generativeai as genai
from google.generativeai.types import RequestOptions
from core.config import config

logger = logging.getLogger(__name__)

# Default timeout untuk API calls (dalam detik)
DEFAULT_TIMEOUT = 30

class AIReplyGenerator:
    """
    Module untuk men-generate draf balasan (reply) yang natural dan kontekstual
    berisi rekomendasi produk beserta link afiliasi untuk diposting di Threads.
    """
    
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        if not self.api_key:
            logger.error("GEMINI_API_KEY belum diatur di environment.")
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_draft(self, post_content: str, category: str, product_name: str, affiliate_link: str, max_retries: int = 3) -> str:
        """
        Men-generate draf balasan berupa teks murni (string) berdasarkan parameter data lengkap.
        
        Args:
            post_content (str): Teks postingan asli pengguna.
            category (str): Kategori produk hasil deteksi AI.
            product_name (str): Nama produk yang dipilih oleh AI.
            affiliate_link (str): URL shp.ee yang sudah dibuat.
            
        Returns:
            str: Teks balasan utuh yang siap dikirim/disimpan.
        """
        prompt = f"""
        Tugas Anda adalah menulis balasan (reply) yang natural, *soft selling*, dan seperti ditulis oleh manusia asli (bukan bot/spam) untuk merespon pengguna di Threads.
        
        Konteks Postingan:
        "{post_content}"
        
        Data Rekomendasi Anda:
        - Kategori Produk: {category}
        - Nama Produk: {product_name}
        - Link Pembelian: {affiliate_link}
        
        Aturan Penulisan:
        1. Gunakan bahasa gaul/santai khas netizen Indonesia (bisa sapa dengan 'kak', 'bro', 'sis', dll. menyesuaikan dengan gaya tulisan poster asli).
        2. Berikan alasan empati yang logis (secara halus) mengapa produk ini menyelesaikan keluhan/masalah mereka.
        3. Wajib cantumkan Link Pembelian secara jelas.
        4. Dilarang memunculkan sapaan formal (seperti "Halo," "Selamat Pagi,").
        5. Dilarang menggunakan kalimat pembuka sistem ("Berikut adalah balasannya:", "Tentu, ini contohnya:"). Langsung tulis draf balasannya saja.
        6. Pertahankan agar balasan tetap singkat dan padat (2-4 kalimat).
        """

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Men-generate draf balasan (Percobaan {attempt}/{max_retries})...")
                
                # Tidak menggunakan JSON config karena kita butuh plain text string utuh
                response = self.model.generate_content(
                    prompt,
                    request_options=RequestOptions(timeout=DEFAULT_TIMEOUT * 1000)  # Convert to ms
                )
                
                draft = response.text.strip()
                
                if draft:
                    logger.info("Berhasil membuat draf balasan yang natural.")
                    return draft
                else:
                    raise ValueError("Teks kosong dikembalikan oleh AI.")
                    
            except Exception as e:
                logger.warning(f"Error pada AIReplyGenerator: {e}", exc_info=True)
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info(f"Mencoba ulang dalam {wait_time} detik...")
                    time.sleep(wait_time)
                else:
                    logger.error("Gagal men-generate draf balasan setelah batas maksimal retry.", exc_info=True)
                    
        # Fallback sangat basic apabila AI mati total
        return f"Wah menarik nih kak. Kalau masih nyari {category}, bisa cek {product_name} ini, lumayan oke kok: {affiliate_link}"
