from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf.csrf import CSRFProtect
import os
import sys

# Memastikan kita bisa import modul dari direktori root (core, database, modules)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.config import config
from database.db import SessionLocal
from database.models import ThreadPost

app = Flask(__name__)
# Gunakan secret key yang persisten dari environment variable
app.secret_key = config.FLASK_SECRET_KEY
csrf = CSRFProtect(app)

@app.route('/')
def index():
    """Halaman Utama: Menampilkan List Post dengan Filter dan Sorting"""
    db = SessionLocal()
    try:
        # 1. Parameter Filter
        status_filter = request.args.get('status', 'all')

        # 2. Parameter Sorting
        sort_by = request.args.get('sort', 'desc') # desc, asc

        query = db.query(ThreadPost)

        # Logic Filtering
        if status_filter != 'all':
            query = query.filter(ThreadPost.status == status_filter.upper())

        # Logic Sorting
        if sort_by == 'asc':
            query = query.order_by(ThreadPost.scraped_at.asc())
        else:
            query = query.order_by(ThreadPost.scraped_at.desc())

        # Simple Pagination (Limit 20 posts)
        posts = query.limit(20).all()
        return render_template('index.html', posts=posts, status=status_filter, sort=sort_by)
    finally:
        db.close()

@app.route('/post/<int:post_id>', methods=['GET'])
def detail(post_id):
    """Halaman Detail: Melihat informasi spesifik dan form aksi (Approve/Edit/Skip)"""
    db = SessionLocal()
    try:
        post = db.query(ThreadPost).filter(ThreadPost.id == post_id).first()
        if not post:
            flash("Post tidak ditemukan dalam database", "error")
            return redirect(url_for('index'))
        return render_template('detail.html', post=post)
    finally:
        db.close()

@app.route('/post/<int:post_id>/action', methods=['POST'])
def action(post_id):
    """Handler Aksi: Menangkap action_type dari form detail (approve, edit, skip)"""
    action_type = request.form.get('action_type')
    new_draft = request.form.get('reply_draft')
    
    db = SessionLocal()
    post = db.query(ThreadPost).filter(ThreadPost.id == post_id).first()
    
    if not post:
        flash("Post tidak ditemukan", "error")
        db.close()
        return redirect(url_for('index'))
        
    try:
        from main import _update_status
        # Aksi 1: Approve (Menyetujui draft saat ini)
        if action_type == 'approve':
            post.reply_draft = new_draft # simpan revisi (jika ada) dan approve
            db.commit()
            _update_status(post.post_id, "APPROVED", "Disetujui oleh admin")
            flash("Post berhasil disetujui (Approved).", "success")
            
        # Aksi 2: Edit (Hanya menyimpan draf baru, belum mengubah status)
        elif action_type == 'edit':
            if new_draft:
                post.reply_draft = new_draft
                db.commit()
                flash("Draft balasan berhasil diperbarui (Edit tersimpan).", "success")
            else:
                flash("Draft tidak boleh kosong jika ingin menyimpan.", "error")
                
        # Aksi 3: Skip (Abaikan post ini, tidak akan dikirim bot)
        elif action_type == 'skip':
            post.reply_draft = ""
            db.commit()
            _update_status(post.post_id, "SKIPPED", "Dilewati oleh admin")
            flash("Post dilewati (Skipped).", "info")
            
    except Exception as e:
        db.rollback()
        flash(f"Terjadi kesalahan saat memproses aksi: {e}", "error")
    finally:
        db.close()
        
    return redirect(url_for('detail', post_id=post_id))

@app.route('/analytics')
def analytics():
    """Halaman Analytics: Menampilkan metrik postingan."""
    from sqlalchemy import func
    db = SessionLocal()
    try:
        # Total berdasarkan Status
        status_counts = dict(db.query(ThreadPost.status, func.count(ThreadPost.id)).group_by(ThreadPost.status).all())
        total_posts = db.query(func.count(ThreadPost.id)).scalar() or 0
        
        # Total per status
        total_analyzed = status_counts.get('ANALYZED', 0)
        total_approved = status_counts.get('APPROVED', 0)
        total_skipped = status_counts.get('SKIPPED', 0)
        total_sent = status_counts.get('SENT', 0)
        total_failed = status_counts.get('FAILED', 0)
        
        # Category Analytics
        categories = db.query(ThreadPost.category, func.count(ThreadPost.id)).filter(ThreadPost.category != None).group_by(ThreadPost.category).all()
        
        # Intent Analytics
        intent_stats = db.query(
            func.avg(ThreadPost.intent_score).label('avg'),
            func.max(ThreadPost.intent_score).label('max'),
            func.min(ThreadPost.intent_score).label('min')
        ).first()
        
        avg_score = round(intent_stats.avg, 2) if intent_stats.avg else 0
        max_score = intent_stats.max if intent_stats.max else 0
        min_score = intent_stats.min if intent_stats.min else 0
        
        # Daily Analytics (Posts per day, Approved per day, Sent per day)
        # Using SQLite date function
        daily_stats = db.query(
            func.date(ThreadPost.scraped_at).label('day'),
            func.count(ThreadPost.id).label('posts'),
            func.sum(func.case((ThreadPost.status == 'APPROVED', 1), else_=0)).label('approved'),
            func.sum(func.case((ThreadPost.status == 'SENT', 1), else_=0)).label('sent')
        ).group_by('day').order_by(func.date(ThreadPost.scraped_at).desc()).limit(10).all()
        
        return render_template('analytics.html', 
                               total=total_posts,
                               analyzed=total_analyzed,
                               approved=total_approved,
                               skipped=total_skipped,
                               sent=total_sent,
                               failed=total_failed,
                               categories=categories,
                               avg_score=avg_score,
                               max_score=max_score,
                               min_score=min_score,
                               daily_stats=daily_stats)
    finally:
        db.close()

def run_dashboard(host="0.0.0.0", port=5000, debug=False):
    """Fungsi entry point untuk menjalankan server Flask"""
    print(f"Memulai Dashboard Threads Affiliate System di http://{host}:{port} ...")
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_dashboard()
