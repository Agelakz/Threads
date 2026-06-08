import logging
from database.db import SessionLocal
from database.models import ProductMetric

logger = logging.getLogger(__name__)

class RankingEngine:
    """Engine untuk menghitung dan menyimpan skor produk."""
    
    def calculate_product_score(self, click_count: int, conversion_count: int, rating: float, review_count: int) -> int:
        """
        Rumus: (Click * 10) + (Conversion * 50) + (Rating * 10) + Review Count
        """
        try:
            score = (click_count * 10) + (conversion_count * 50) + int(rating * 10) + review_count
            return score
        except Exception as e:
            logger.error(f"Error calculating product score: {e}", exc_info=True)
            return 0

    def update_or_create_metric(self, product_name: str, category: str, rating: float = 0.0, review_count: int = 0) -> int:
        """
        Untuk MVP, rating dan review_count bisa di-pass dari scraper (jika ada).
        Mengupdate data di DB dan mengembalikan score terbaru.
        """
        db = SessionLocal()
        try:
            metric = db.query(ProductMetric).filter(ProductMetric.product_name == product_name).first()
            if not metric:
                metric = ProductMetric(
                    product_name=product_name,
                    category=category,
                    click_count=0,
                    conversion_count=0
                )
                db.add(metric)
                
            # Asumsi rating dan review_count tidak disimpan di tabel metrik saat ini,
            # hanya click dan conversion. Tapi kita hitung score berdasarkan parameter runtime juga.
            score = self.calculate_product_score(metric.click_count, metric.conversion_count, rating, review_count)
            metric.product_score = score
            
            db.commit()
            return score
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update ProductMetric for {product_name}: {e}", exc_info=True)
            return 0
        finally:
            db.close()

    def get_score(self, product_name: str) -> int:
        """Mendapatkan skor produk dari database."""
        db = SessionLocal()
        try:
            metric = db.query(ProductMetric).filter(ProductMetric.product_name == product_name).first()
            return metric.product_score if metric else 0
        finally:
            db.close()
