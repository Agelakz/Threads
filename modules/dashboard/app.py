from flask import Flask, render_template, request, redirect, url_for, flash
import os
import sys

# Memastikan kita bisa import modul dari direktori root (core, database, modules)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from database.db import SessionLocal
from database.models import ThreadPost

app = Flask(__name__)
# Menggunakan random string sederhana untuk Flash messages session MVP
app.secret_key = os.urandom(24)

@app.route('/')
def index():
    """Halaman Utama: Menampilkan List Post dengan Filter dan Sorting"""
    db = SessionLocal()
    
    # 1. Parameter Filter
    status_filter = request.args.get('status', 'pending') # pending, processed
    
    # 2. Parameter Sorting
    sort_by = request.args.get('sort', 'desc') # desc, asc
    
    query = db.query(ThreadPost)
    
    # Logic Filtering
    if status_filter == 'pending':
        query = query.filter(ThreadPost.is_processed == False)
    elif status_filter == 'processed':
        query = query.filter(ThreadPost.is_processed == True)

    # Logic Sorting
    if sort_by == 'asc':
        query = query.order_by(ThreadPost.scraped_at.asc())
    else:
        query = query.order_by(ThreadPost.scraped_at.desc())
        
    posts = query.all()
    db.close()
    
    return render_template('index.html', posts=posts, status=status_filter, sort=sort_by)

@app.route('/post/<int:post_id>', methods=['GET'])
def detail(post_id):
    """Halaman Detail: Melihat informasi spesifik dan form aksi (Approve/Edit/Skip)"""
    db = SessionLocal()
    post = db.query(ThreadPost).filter(ThreadPost.id == post_id).first()
    db.close()
    
    if not post:
        flash("Post tidak ditemukan dalam database", "error")
        return redirect(url_for('index'))
        
    return render_template('detail.html', post=post)

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
        # Aksi 1: Approve (Menyetujui draft saat ini)
        if action_type == 'approve':
            post.is_processed = True
            post.reply_draft = new_draft # simpan revisi (jika ada) dan approve
            flash("Post berhasil disetujui (Approved).", "success")
            
        # Aksi 2: Edit (Hanya menyimpan draf baru, belum mengubah status)
        elif action_type == 'edit':
            if new_draft:
                post.reply_draft = new_draft
                flash("Draft balasan berhasil diperbarui (Edit tersimpan).", "success")
            else:
                flash("Draft tidak boleh kosong jika ingin menyimpan.", "error")
                
        # Aksi 3: Skip (Abaikan post ini, tidak akan dikirim bot)
        elif action_type == 'skip':
            post.is_processed = True
            post.reply_draft = "" # Kosongkan atau bisa tambahkan logic khusus 'SKIPPED'
            flash("Post dilewati (Skipped).", "info")
            
        db.commit()
    except Exception as e:
        db.rollback()
        flash(f"Terjadi kesalahan saat memproses aksi: {e}", "error")
    finally:
        db.close()
        
    return redirect(url_for('detail', post_id=post_id))

def run_dashboard(host='127.0.0.1', port=5000, debug=True):
    """Fungsi entry point untuk menjalankan server Flask"""
    print(f"Memulai Dashboard Threads Affiliate System di http://{host}:{port} ...")
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_dashboard()
