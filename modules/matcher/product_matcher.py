import json
import time
import logging
from typing import List, Dict
import google.generativeai as genai
from core.config import config
from modules.matcher.ranking_engine import RankingEngine

logger = logging.getLogger(__name__)

class AIProductMatcher:
    """
    Module untuk mengevaluasi daftar produk kandidat dan mencocokkannya 
    dengan konteks (intent) dari sebuah postingan media sosial secara spesifik
    menggunakan Google Gemini AI.
    """
    
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        if not self.api_key:
            logger.error("GEMINI_API_KEY belum diatur di environment.")
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.ranking_engine = RankingEngine()

    def match_product(self, post_content: str, candidate_products: List[Dict], max_retries: int = 3) -> dict:
        """
        Memilih produk terbaik dari daftar kandidat berdasarkan kecocokan 
        dengan postingan pengguna.
        
        Args:
            post_content (str): Teks postingan asli dari Threads
            candidate_products (List[Dict]): Daftar produk dari Shopee (harus memuat 'name' dan 'price')
            
        Returns:
            dict: {"product_name": str, "category": str}
        """
        
        if not candidate_products:
            logger.warning("Daftar kandidat produk kosong, pencocokan dibatalkan.")
            return {"product_name": "Tidak Ditemukan", "category": "Unknown"}

        # Enrich products with scores and sort them
        enriched_products = []
        for p in candidate_products:
            score = self.ranking_engine.get_score(p.get("name", ""))
            p["score"] = score
            enriched_products.append(p)
            
        # Sort descending by score
        enriched_products.sort(key=lambda x: x["score"], reverse=True)

        # Merangkai kandidat produk menjadi teks agar dapat diproses oleh LLM
        products_text = ""
        for idx, p in enumerate(enriched_products, 1):
            products_text += f"{idx}. {p.get('name', 'Unknown')} - {p.get('price', 'Unknown')} (Product Score: {p.get('score', 0)})\n"

        prompt = f"""
        Anda adalah asisten rekomendasi produk belanja online yang ahli.
        
        Postingan Media Sosial Pengguna:
        "{post_content}"
        
        Daftar Kandidat Produk:
        {products_text}
        
        Tugas Anda:
        1. Analisis konteks dan kebutuhan dari postingan pengguna.
        2. Pilih SATU produk dari daftar kandidat di atas yang paling akurat dan relevan untuk ditawarkan.
        3. Jika ada beberapa produk yang sama relevannya, PRIORITASKAN produk dengan Product Score tertinggi.
        4. Sebutkan nama produk secara persis seperti di daftar.
        5. Tentukan satu kategori umum untuk produk tersebut (misal: Fashion, Beauty, Gaming, Electronics, Home, Health).
        
        Balas HANYA dengan format JSON ketat sesuai schema di bawah ini tanpa karakter backticks Markdown:
        {{
            "product_name": "Nama produk yang paling relevan dari daftar",
            "category": "Kategori produk"
        }}
        """

        # Memastikan Gemini menjawab hanya menggunakan JSON
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
        )

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Mencocokkan post dengan produk (Percobaan {attempt}/{max_retries})...")
                response = self.model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                
                result = json.loads(response.text)
                
                # Validasi kelengkapan keys
                if "product_name" in result and "category" in result:
                    logger.info(f"Match sukses! Produk: {result['product_name']} | Kategori: {result['category']}")
                    return result
                else:
                    raise ValueError(f"Respon JSON dari AI kehilangan schema yang disyaratkan: {result}")

            except Exception as e:
                logger.warning(f"Error AIProductMatcher: {e}")
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info(f"Mencoba ulang dalam {wait_time} detik...")
                    time.sleep(wait_time)
                else:
                    logger.error("Gagal melakukan pencocokan produk setelah batas maksimal retry.")
                    
        return {
            "product_name": "Tidak Ditemukan",
            "category": "Unknown"
        }
