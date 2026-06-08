import argparse
import logging
import sys

# Konfigurasi logging dasar sebelum memuat modul lain
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

from database.db import init_db
from modules.threads.monitor import ThreadsMonitor
from modules.threads.poster import ThreadsPoster
from modules.ai.intent_scorer import AIIntentScorer
from modules.ai.category_detector import AICategoryDetector
from modules.shopee.product_finder import ShopeeProductFinder
from modules.matcher.product_matcher import AIProductMatcher
from modules.shopee.link_generator import ShopeeLinkGenerator
from modules.matcher.reply_generator import AIReplyGenerator
from modules.dashboard.app import run_dashboard

def run_pipeline(keyword: str, limit: int = 5, headless: bool = True):
    """
    Menjalankan seluruh pipeline secara end-to-end:
    Threads -> Scorer -> Category -> Shopee -> Matcher -> Link -> Reply -> DB
    """
    logger.info(f"=== Memulai Pipeline Bot ===")
    logger.info(f"Target Keyword: '{keyword}', Limit: {limit} post")

    # 1. Scrape Threads
    monitor = ThreadsMonitor()
    raw_posts = monitor.search_and_collect(keyword, limit=limit, headless=headless)
    
    if not raw_posts:
        logger.info("Tidak ada post baru yang ditemukan. Pipeline dihentikan.")
        return

    # Inisialisasi modul-modul
    intent_scorer = AIIntentScorer()
    category_detector = AICategoryDetector()
    product_finder = ShopeeProductFinder()
    product_matcher = AIProductMatcher()
    link_generator = ShopeeLinkGenerator()
    reply_generator = AIReplyGenerator()

    # 2. Proses masing-masing post
    for post in raw_posts:
        post_content = post["content"]
        logger.info(f"--- Memproses Post ID: {post['post_id']} ---")
        
        # Step A: Intent Scoring
        intent_res = intent_scorer.analyze_intent(post_content)
        intent_score = intent_res.get("score", 0)
        
        if intent_score < 70:
            logger.info(f"Intent rendah ({intent_score}). Diabaikan.")
            _update_status(post["post_id"], "SKIPPED", f"Low intent score: {intent_score}")
            continue
            
        _update_status(post["post_id"], "ANALYZED", "AI Intent Scorer selesai")
            
        # Step B: Category Detection
        cat_res = category_detector.detect_category(post_content)
        category = cat_res.get("category", "Unknown")
        
        # Step C: Shopee Search (Gunakan keyword spesifik dari kategori + keyword)
        # Jika kategori tidak terdeteksi, kita skip prefixnya
        search_kw = f"{category} {keyword}".strip() if category != "Unknown" else keyword
        products = product_finder.search_products(search_kw, limit=3, headless=headless)
        
        if not products:
            logger.info("Tidak ditemukan produk di Shopee yang relevan. Diabaikan.")
            continue
            
        # Step D: Product Matching
        match_res = product_matcher.match_product(post_content, products)
        product_name = match_res.get("product_name", "")
        
        if not product_name or product_name == "Tidak Ditemukan":
            logger.info("Tidak ada kecocokan produk yang tinggi. Diabaikan.")
            continue
            
        # Find the matched product from the list to get URL
        best_match = None
        for p in products:
            if p.get("name", "") == product_name:
                best_match = p
                break
        if not best_match and products:
            # Fallback to first product if name doesn't match exactly
            best_match = products[0]
            
        if not best_match:
            logger.info("Tidak ada produk yang cocok. Diabaikan.")
            continue
            
        # Step E: Link Generation
        affiliate_url = link_generator.generate_affiliate_link(best_match["url"], headless=headless)
        if not affiliate_url:
            logger.info("Gagal men-generate link affiliate Shopee. Diabaikan.")
            continue
            
        # Step F: Reply Generation
        reply_draft = reply_generator.generate_draft(
            post_content=post_content,
            category=category,
            product_name=product_name,
            affiliate_link=affiliate_url
        )
        
        # Step G: Update Database
        _update_post_fields(post["post_id"], intent_score, category, reply_draft)
        
        # Biarkan status tetap ANALYZED, tunggu admin Approve di Dashboard
        logger.info(f"Draft balasan berhasil dibuat untuk post {post['post_id']}")

    logger.info("=== Pipeline Selesai ===")

def _update_post_fields(post_id: str, score: int, category: str, reply_draft: str):
    """Fungsi helper untuk mengupdate data post yang sudah masuk di awal."""
    from database.db import SessionLocal
    from database.models import ThreadPost
    
    db = SessionLocal()
    try:
        db_post = db.query(ThreadPost).filter(ThreadPost.post_id == post_id).first()
        if db_post:
            db_post.intent_score = score
            db_post.category = category
            db_post.reply_draft = reply_draft
            db.commit()
    except Exception as e:
        logger.error(f"Gagal update database untuk post {post_id}: {e}")
        db.rollback()
    finally:
        db.close()

def _update_status(post_id: str, new_status: str, reason: str = ""):
    from database.db import SessionLocal
    from database.models import ThreadPost, SystemLog
    
    db = SessionLocal()
    try:
        db_post = db.query(ThreadPost).filter(ThreadPost.post_id == post_id).first()
        if db_post:
            old_status = db_post.status
            db_post.status = new_status
            
            # Tambahkan log perubahan status
            log_msg = f"Post {post_id} status changed: {old_status} -> {new_status}"
            if reason:
                log_msg += f" ({reason})"
                
            new_log = SystemLog(level="INFO", module="Workflow", message=log_msg)
            db.add(new_log)
            db.commit()
            logger.info(log_msg)
    except Exception as e:
        logger.error(f"Gagal update status post {post_id}: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Threads Affiliate Intelligence System")
    parser.add_argument('--keyword', type=str, help='Keyword yang dicari di Threads (contoh: "rekomendasi skincare")')
    parser.add_argument('--limit', type=int, default=5, help='Jumlah maksimal post yang di-scrape')
    parser.add_argument('--visible', action='store_true', help='Jalankan browser tanpa mode headless (terlihat)')
    parser.add_argument('--dashboard', action='store_true', help='Jalankan web dashboard')
    parser.add_argument('--post', action='store_true', help='Jalankan auto-poster untuk mengirim balasan yang di-approve')

    args = parser.parse_args()

    # Pastikan database ada sebelum memulai apapun
    init_db()

    if args.dashboard:
        logger.info("Menjalankan Dashboard UI...")
        run_dashboard(debug=False)
    elif args.post:
        logger.info("Menjalankan Auto-Poster...")
        poster = ThreadsPoster()
        count = poster.post_all_approved(headless=not args.visible)
        logger.info(f"Selesai. {count} balasan terkirim.")
    elif args.keyword:
        run_pipeline(args.keyword, args.limit, headless=not args.visible)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
