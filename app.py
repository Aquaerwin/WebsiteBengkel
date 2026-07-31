from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
import sqlite3
from datetime import datetime, date, timedelta
import random
import string
import os
import re
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
import csv
from io import StringIO

load_dotenv()

# Initialize Flask App
app = Flask(__name__, static_url_path='', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

@app.template_filter('formatdate')
def formatdate(value, format='%d-%m-%Y'):
    if isinstance(value, str):
        try:
            return datetime.strptime(value, '%Y-%m-%d').strftime(format)
        except ValueError:
            return value
    return value.strftime(format)

# Security Configurations
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.permanent_session_lifetime = timedelta(minutes=30)

# Security Headers (Production Hardening)
csp = {
    'default-src': ["'self'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com", "https://fonts.gstatic.com"],
    'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
    'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com"],
    'img-src': ["'self'", "data:"]
}
talisman = Talisman(app, content_security_policy=csp, force_https=False) # force_https=False for local dev

csrf = CSRFProtect(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)

# Konfigurasi Batas Maksimal Booking per hari
MAX_BOOKING_PER_DAY = 5

# Database Configuration
db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'db_bengkel')
}

def get_db_connection():
    try:
        connection = sqlite3.connect('database.db')
        connection.row_factory = sqlite3.Row
        return connection
    except sqlite3.Error as err:
        print(f"Error connecting to SQLite: {err}")
        return None

def log_activity(user_id, role, action, target_table, target_id, old_value, new_value):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO audit_logs (user_id, role, action, target_table, target_id, old_value, new_value, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, role, action, target_table, target_id, old_value, new_value, request.remote_addr))
            conn.commit()
        except sqlite3.Error as err:
            print(f"Error logging: {err}")
        finally:
            cursor.close()
            conn.close()

# Route: Home Page
@app.route('/')
def index():
    return render_template('index.html')

# API: Ketersediaan Tanggal
@app.route('/api/availability')
def check_availability():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database error"})
        
    cursor = conn.cursor()
    
    # 1. Ambil data hari libur
    cursor.execute("SELECT tanggal, keterangan FROM holidays")
    holiday_rows = cursor.fetchall()
    holidays = {}
    for row in holiday_rows:
        tanggal_str = row['tanggal']
        holidays[tanggal_str] = row['keterangan']
        
    # 2. Ambil data jumlah booking per hari (hanya yang tidak Batal)
    cursor.execute("""
        SELECT tanggal_booking, COUNT(id) as total 
        FROM bookings 
        WHERE status != 'Batal' 
        GROUP BY tanggal_booking
    """)
    booking_rows = cursor.fetchall()
    bookings = {}
    for row in booking_rows:
        tanggal_str = row['tanggal_booking']
        bookings[tanggal_str] = row['total']
        
    cursor.close()
    conn.close()
    
    return jsonify({
        "holidays": holidays,
        "bookings": bookings,
        "max_per_day": MAX_BOOKING_PER_DAY
    })

# Route: Health Check (Monitoring)
@app.route('/api/health')
@limiter.exempt
def health_check():
    conn = get_db_connection()
    if conn:
        conn.close()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    return jsonify({"status": "unhealthy", "database": "disconnected"}), 503


# Route: Register Customer
@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per hour")
def register():
    if 'loggedin' in session:
        return redirect(url_for('dashboard'))

    error = ''
    if request.method == 'POST':
        nama = request.form.get('nama')
        email = request.form.get('email')
        no_hp = request.form.get('no_hp')
        password = request.form.get('password')

        # Password Policy
        if len(password) < 8 or len(password) > 128:
            error = 'Password harus antara 8 hingga 128 karakter.'
        elif password == email:
            error = 'Password tidak boleh sama dengan email.'
        elif not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password):
            error = 'Password harus mengandung huruf besar, huruf kecil, dan angka.'
        else:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
                account = cursor.fetchone()

                if account:
                    error = 'Email tersebut sudah terdaftar! Silakan Login.'
                else:
                    try:
                        hashed_pw = generate_password_hash(password)
                        cursor.execute("INSERT INTO users (nama, email, no_hp, password, role) VALUES (?, ?, ?, ?, 'customer')", (nama, email, no_hp, hashed_pw))
                        conn.commit()
                        new_user_id = cursor.lastrowid
                        log_activity(new_user_id, 'customer', 'Register', 'users', new_user_id, None, None)
                        return """
                        <script>
                            alert('Pendaftaran Berhasil! Silakan Login.');
                            window.location.href = '/login';
                        </script>
                        """
                    except sqlite3.Error as err:
                        error = 'Gagal mendaftar, terjadi kesalahan server.'
                    finally:
                        cursor.close()
                        conn.close()
                
                if cursor: cursor.close()
                if conn: conn.close()
            else:
                error = 'Koneksi database gagal.'

    return render_template('register.html', error=error)


# Route: Login
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if 'loggedin' in session:
        return redirect(url_for('dashboard'))

    error = ''
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            account = cursor.fetchone()
            
            cursor.close()
            conn.close()

            if account:
                account_dict = dict(account)
                if check_password_hash(account_dict['password'], password):
                    session['loggedin'] = True
                    session['id'] = account_dict['id']
                    session['nama'] = account_dict.get('nama', '')
                    session['email'] = account_dict['email']
                    session['no_hp'] = account_dict.get('no_hp', '')
                    session['role'] = account_dict['role']
                    
                    log_activity(account_dict['id'], account_dict['role'], 'Login', 'users', account_dict['id'], None, None)
                    
                    return redirect(url_for('dashboard'))
                else:
                    error = 'Email atau Password salah!'
            else:
                error = 'Email atau Password salah!'
        else:
            error = 'Koneksi database gagal.'

    return render_template('login.html', error=error)

# Route: Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# Route: Handle Booking Form Submission
@app.route('/api/booking', methods=['POST'])
@limiter.limit("60 per minute")
def submit_booking():
    if 'loggedin' not in session:
        return """
        <script>
            alert('Anda harus Login atau Mendaftar terlebih dahulu untuk melakukan Booking!');
            window.location.href = '/login';
        </script>
        """

    if request.method == 'POST':
        user_id = session['id']
        nama = request.form.get('nama')
        tanggal_booking = request.form.get('tanggal_booking')
        layanan_id = request.form.get('layanan_id')
        keluhan_kerusakan = request.form.get('keluhan_kerusakan')

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            
            # Cek Keamanan di sisi Server: Validasi Tanggal (Tidak boleh masa lalu)
            try:
                tanggal_obj = datetime.strptime(tanggal_booking, '%Y-%m-%d').date()
                if tanggal_obj < date.today():
                    cursor.close(); conn.close()
                    return "<script>alert('Gagal: Anda tidak bisa booking di tanggal yang sudah berlalu (masa lalu)!'); window.history.back();</script>"
            except ValueError:
                cursor.close(); conn.close()
                return "<script>alert('Gagal: Format tanggal tidak valid!'); window.history.back();</script>"
            
            # Cek Keamanan di sisi Server (Apakah kuota penuh atau hari libur?)
            cursor.execute("SELECT * FROM holidays WHERE tanggal = ?", (tanggal_booking,))
            is_holiday = cursor.fetchone()
            if is_holiday:
                cursor.close(); conn.close()
                return "<script>alert('Gagal: Tanggal tersebut adalah hari libur (" + is_holiday['keterangan'] + ")'); window.history.back();</script>"
                
            cursor.execute("SELECT COUNT(id) as total FROM bookings WHERE tanggal_booking = ? AND status != 'Batal'", (tanggal_booking,))
            current_bookings = cursor.fetchone()['total']
            if current_bookings >= MAX_BOOKING_PER_DAY:
                cursor.close(); conn.close()
                return "<script>alert('Gagal: Maaf, kuota bengkel untuk tanggal tersebut sudah penuh (Maksimal " + str(MAX_BOOKING_PER_DAY) + ").'); window.history.back();</script>"
            
            # Generate Random Booking Code
            random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            kode_booking = f"TRL-{random_chars}"

            # Jika lolos cek, masukkan ke database
            try:
                sql = """
                INSERT INTO bookings (user_id, nama, tanggal_booking, layanan_id, keluhan_kerusakan, status, kode_booking)
                VALUES (?, ?, ?, ?, ?, 'Pending', ?)
                """
                val = (user_id, nama, tanggal_booking, layanan_id, keluhan_kerusakan, kode_booking)
                cursor.execute(sql, val)
                conn.commit()
                
                log_activity(user_id, session.get('role', 'customer'), 'Create Booking', 'bookings', cursor.lastrowid, None, kode_booking)
                
                return """
                <script>
                    alert('Booking berhasil! Anda bisa memantau statusnya di Dashboard.');
                    window.location.href = '/dashboard';
                </script>
                """
            except sqlite3.Error as err:
                print(f"Error: {err}")
                return "Terjadi kesalahan pada server saat menyimpan data."
            finally:
                cursor.close()
                conn.close()
        else:
            return "Koneksi database gagal. Pastikan MySQL sudah menyala."


# Route: Dashboard (Admin & Customer)
@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    bookings = []
    holidays = []
    
    if session['role'] == 'admin':
        if conn:
            cursor = conn.cursor()
            
            # Pagination and Search Setup
            page = request.args.get('page', 1, type=int)
            search = request.args.get('search', '')
            per_page = 10
            offset = (page - 1) * per_page
            search_query = f"%{search}%"
            
            # Count Total for Pagination
            count_query = "SELECT COUNT(b.id) as total FROM bookings b JOIN users u ON b.user_id = u.id WHERE b.kode_booking LIKE ? OR b.nama LIKE ? OR u.no_hp LIKE ?"
            cursor.execute(count_query, (search_query, search_query, search_query))
            total_records = cursor.fetchone()['total']
            total_pages = (total_records + per_page - 1) // per_page

            # Ambil data bookings beserta nomor hp pelanggan (with search and pagination)
            query = """
            SELECT b.id, b.kode_booking, b.nama, b.tanggal_booking, b.keluhan_kerusakan, b.status, l.nama_layanan, u.no_hp
            FROM bookings b
            JOIN layanan l ON b.layanan_id = l.id
            JOIN users u ON b.user_id = u.id
            WHERE b.kode_booking LIKE ? OR b.nama LIKE ? OR u.no_hp LIKE ?
            ORDER BY b.tanggal_booking DESC, b.id DESC
            LIMIT ? OFFSET ?
            """
            cursor.execute(query, (search_query, search_query, search_query, per_page, offset))
            bookings = cursor.fetchall()
            
            # Ambil data hari libur untuk admin
            cursor.execute("SELECT * FROM holidays ORDER BY tanggal ASC")
            holidays = cursor.fetchall()
            
            cursor.close()
            conn.close()
        return render_template('admin.html', bookings=bookings, holidays=holidays, max_quota=MAX_BOOKING_PER_DAY, page=page, total_pages=total_pages, search=search)
    else:
        # Tampilan Customer
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT b.id, b.kode_booking, b.nama, b.tanggal_booking, b.keluhan_kerusakan, b.status, l.nama_layanan 
            FROM bookings b
            JOIN layanan l ON b.layanan_id = l.id
            WHERE b.user_id = ?
            ORDER BY b.tanggal_booking DESC, b.id DESC
            """, (session['id'],))
            bookings = cursor.fetchall()
            
            # Ambil nomor admin untuk tombol WhatsApp
            cursor.execute("SELECT no_hp FROM users WHERE role = 'admin' LIMIT 1")
            admin_data = cursor.fetchone()
            admin_no_hp = admin_data['no_hp'] if admin_data else "6281234567890"
            
            cursor.close()
            conn.close()
        return render_template('customer.html', bookings=bookings, max_quota=MAX_BOOKING_PER_DAY, admin_hp=admin_no_hp)

# Route: Export Bookings to CSV (Admin Only)
@app.route('/admin/export_bookings')
@limiter.exempt
def export_bookings():
    if 'loggedin' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        query = """
        SELECT b.kode_booking, b.nama, u.no_hp, b.tanggal_booking, l.nama_layanan, b.keluhan_kerusakan, b.status
        FROM bookings b
        JOIN layanan l ON b.layanan_id = l.id
        JOIN users u ON b.user_id = u.id
        ORDER BY b.tanggal_booking DESC
        """
        cursor.execute(query)
        bookings = cursor.fetchall()
        cursor.close()
        conn.close()
        
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['Kode Booking', 'Nama Pelanggan', 'No HP', 'Tanggal Servis', 'Layanan', 'Keluhan', 'Status'])
        for b in bookings:
            cw.writerow([
                b['kode_booking'], 
                b['nama'], 
                b['no_hp'], 
                b['tanggal_booking'], 
                b['nama_layanan'], 
                b['keluhan_kerusakan'], 
                b['status']
            ])
            
        output = si.getvalue()
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=laporan_booking_{date.today().strftime('%Y%m%d')}.csv"}
        )
    return "Koneksi database gagal.", 500

# Route: Backup Database (Admin Only)
@app.route('/admin/backup_db')
@limiter.exempt
def backup_db():
    if 'loggedin' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if not conn:
        return "Koneksi database gagal", 500
        
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    
    sql_dump = f"-- Database Backup generated on {date.today()}\n\n"
    
    for table in tables:
        cursor.execute(f"SHOW CREATE TABLE {table}")
        create_table_stmt = cursor.fetchone()[1]
        sql_dump += f"DROP TABLE IF EXISTS `{table}`;\n"
        sql_dump += f"{create_table_stmt};\n\n"
        
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        
        if rows:
            cursor.execute(f"SHOW COLUMNS FROM {table}")
            columns = [col[0] for col in cursor.fetchall()]
            cols_str = ", ".join([f"`{c}`" for c in columns])
            
            for row in rows:
                values = []
                for val in row:
                    if val is None:
                        values.append("NULL")
                    elif isinstance(val, (int, float)):
                        values.append(str(val))
                    else:
                        # Escape string values
                        escaped_val = str(val).replace("'", "''").replace("\\", "\\\\")
                        values.append(f"'{escaped_val}'")
                
                vals_str = ", ".join(values)
                sql_dump += f"INSERT INTO `{table}` ({cols_str}) VALUES ({vals_str});\n"
        sql_dump += "\n\n"
    
    cursor.close()
    conn.close()
    
    return Response(
        sql_dump,
        mimetype="application/sql",
        headers={"Content-disposition": f"attachment; filename=backup_bengkel_{date.today().strftime('%Y%m%d')}.sql"}
    )

# Route: Update Status Booking (Admin)
@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if 'loggedin' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    status_baru = request.form.get('status')
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Ambil status lama untuk log
            cursor.execute("SELECT status FROM bookings WHERE id = ?", (id,))
            booking_lama = cursor.fetchone()
            status_lama = booking_lama['status'] if booking_lama else None
            
            cursor.execute("UPDATE bookings SET status = ? WHERE id = ?", (status_baru, id))
            conn.commit()
            
            log_activity(session['id'], session['role'], 'Update Status', 'bookings', id, status_lama, status_baru)
        except sqlite3.Error as err:
            print(f"Error: {err}")
        finally:
            cursor.close()
            conn.close()
            
    return redirect(url_for('dashboard'))

# Route: Tambah Hari Libur (Admin)
@app.route('/admin/add_holiday', methods=['POST'])
def add_holiday():
    if 'loggedin' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    tanggal = request.form.get('tanggal')
    keterangan = request.form.get('keterangan')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO holidays (tanggal, keterangan) VALUES (?, ?)", (tanggal, keterangan))
            conn.commit()
            
            log_activity(session['id'], session['role'], 'Add Holiday', 'holidays', cursor.lastrowid, None, tanggal)
        except sqlite3.Error as err:
            print(f"Error: {err}")
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('dashboard'))

# Route: Hapus Hari Libur (Admin)
@app.route('/admin/delete_holiday/<int:id>', methods=['POST'])
def delete_holiday(id):
    if 'loggedin' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM holidays WHERE id = ?", (id,))
            conn.commit()
            
            log_activity(session['id'], session['role'], 'Delete Holiday', 'holidays', id, None, None)
        except sqlite3.Error as err:
            print(f"Error: {err}")
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    print("Membuka server di http://127.0.0.1:5000")
    app.run(debug=False)
