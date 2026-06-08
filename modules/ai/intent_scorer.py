import json
import time
import logging
import google.generativeai as genai
from google.generativeai.types import RequestOptions
from core.config import config

logger = logging.getLogger(__name__)

# Default timeout untuk API calls (dalam detik)
DEFAULT_TIMEOUT = 30

class AIIntentScorer:
    """
    Module untuk menganalisis teks (post) dan memberikan skor niat pembelian (buying intent)
    serta status kelayakan untuk dibalas dengan link afiliasi menggunakan Google Gemini AI.
    """
    
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        if not self.api_key:
            logger.error("GEMINI_API_KEY belum diatur di environment/config.")
            
        genai.configure(api_key=self.api_key)
        
        # Menggunakan gemini-1.5-flash untuk keseimbangan antara kecepatan dan kecerdasan
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def analyze_intent(self, post_content: str, max_retries: int = 3) -> dict:
        """
        Menganalisis teks menggunakan Gemini API.
        Dilengkapi dengan Retry Mechanism (Exponential Backoff).
        
        Returns:
            dict: {"score": int, "status": str}
        """
        prompt = f"""
        Sebagai analis Buying Intent, baca postingan media sosial berikut:
        "{post_content}"
        
        Berikan skor (0-100) mengenai seberapa tinggi niat orang ini mencari rekomendasi atau berniat membeli barang.
        Jika skor >= 70, status = "LAYAK", jika < 70 status = "TIDAK LAYAK".
        
        Balas HANYA dengan JSON schema berikut:
        {{
            "score": integer,
            "status": "LAYAK" atau "TIDAK LAYAK"
        }}
        """

        # Memaksa Gemini API untuk merespon dalam format JSON murni
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
        )

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Menganalisis intent post (Percobaan {attempt}/{max_retries})...")
                response = self.model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    request_options=RequestOptions(timeout=DEFAULT_TIMEOUT * 1000)  # Convert to ms
                )
                
                result = json.loads(response.text)
                
                # Validasi kunci dictionary dari hasil AI
                if "score" in result and "status" in result:
                    logger.info(f"Analisis sukses. Skor: {result['score']}, Status: {result['status']}")
                    return result
                else:
                    raise ValueError(f"Respon JSON kehilangan key 'score' atau 'status': {result}")

            except Exception as e:
                logger.warning(f"Error saat memanggil Gemini API: {e}", exc_info=True)
                
                # Retry Mechanism
                if attempt < max_retries:
                    wait_time = 2 ** attempt # Exponential backoff: 2s, 4s, ...
                    logger.info(f"Retrying dalam {wait_time} detik...")
                    time.sleep(wait_time)
                else:
                    logger.error("Gagal memanggil Gemini API setelah batas maksimal retry.", exc_info=True)
                    
        # Fallback default jika gagal seluruhnya
        return {
            "score": 0,
            "status": "ERROR"
        }
