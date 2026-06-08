import json
import time
import logging
import google.generativeai as genai
from google.generativeai.types import RequestOptions
from core.config import config

logger = logging.getLogger(__name__)

# Default timeout untuk API calls (dalam detik)
DEFAULT_TIMEOUT = 30

class AICategoryDetector:
    """
    Module untuk mendeteksi dan mengklasifikasikan kategori sebuah post
    ke dalam daftar kategori yang telah ditentukan menggunakan Google Gemini AI.
    """
    
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        if not self.api_key:
            logger.error("GEMINI_API_KEY belum diatur di environment/config.")
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Daftar kategori sesuai dengan instruksi (PRD)
        self.valid_categories = [
            "Fashion", 
            "Beauty", 
            "Gaming", 
            "Electronics", 
            "Home", 
            "Health"
        ]

    def detect_category(self, post_content: str, max_retries: int = 3) -> dict:
        """
        Menganalisis teks menggunakan Gemini API untuk menentukan kategori produk.
        Dilengkapi dengan Retry Mechanism (Exponential Backoff).
        
        Returns:
            dict: {"category": str}
        """
        prompt = f"""
        Sebagai spesialis klasifikasi produk, baca postingan media sosial berikut:
        "{post_content}"
        
        Tentukan kategori produk atau topik belanja yang paling relevan dengan postingan tersebut.
        Anda HANYA boleh memilih SATU kategori dari daftar berikut secara sama persis:
        {', '.join(self.valid_categories)}
        
        Jika tidak masuk ke kategori manapun secara jelas, tebak dan pilih kategori yang paling mendekati dari daftar di atas.
        
        Balas HANYA dengan JSON schema berikut:
        {{
            "category": "NamaKategori"
        }}
        """

        # Memaksa AI mengembalikan JSON schema murni
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
        )

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Mendeteksi kategori post (Percobaan {attempt}/{max_retries})...")
                response = self.model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    request_options=RequestOptions(timeout=DEFAULT_TIMEOUT * 1000)  # Convert to ms
                )
                
                result = json.loads(response.text)
                
                # Validasi JSON key
                if "category" in result:
                    cat = result["category"]
                    
                    # Log peringatan jika AI mulai "berhalusinasi" membuat kategori sendiri
                    if cat not in self.valid_categories:
                        logger.warning(f"AI memberikan kategori di luar daftar baku: {cat}")
                        cat = "Unknown" # Force fallback
                        
                    logger.info(f"Deteksi sukses. Kategori: {cat}")
                    return {"category": cat}
                else:
                    raise ValueError(f"Respon JSON tidak memiliki key 'category': {result}")

            except Exception as e:
                logger.warning(f"Error saat memanggil Gemini API: {e}", exc_info=True)
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying dalam {wait_time} detik...")
                    time.sleep(wait_time)
                else:
                    logger.error("Gagal mendeteksi kategori setelah batas maksimal retry.", exc_info=True)
                    
        # Fallback jika API down sepenuhnya
        return {
            "category": "Unknown"
        }
