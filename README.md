# Website Bengkel Mesin & Cat (Tralala Machinery & Paint)

Proyek Sistem Informasi Bengkel berbasis Web yang mengimplementasikan arsitektur Monolitik dengan keamanan tingkat lanjut dan standar produksi.

## 🛠️ Teknologi yang Digunakan
- **Frontend:** HTML5, CSS3 (Bootstrap 5.3), Vanilla JS, Flatpickr
- **Backend:** Python (Flask), Flask-WTF (CSRF), Flask-Limiter, Flask-Talisman, Python-Dotenv
- **Database:** MySQL

## 🚀 Fitur Utama
- **Autentikasi Aman:** Password Hashing (Bcrypt) dan proteksi *Brute-Force*.
- **Booking Online:** Pelanggan dapat membuat janji temu servis.
- **Admin Dashboard:** Dilengkapi *Search*, *Pagination*, *Export Data* ke Excel (CSV), dan *Backup* Database SQL otomatis.
- **Manajemen Libur:** Admin dapat mengatur tanggal tutup bengkel.
- **Sistem Log:** Pencatatan setiap aktivitas user (Audit Logs).

## 💻 Cara Menjalankan di Lokal (Localhost)

1. **Persiapan Database**
   - Buka XAMPP, nyalakan Apache dan MySQL.
   - Buka PHPMyAdmin, buat database baru bernama `db_bengkel`.
   - Lakukan Import file `database.sql` ke dalam database tersebut.

2. **Persiapan Environtment Variables**
   - Di dalam folder utama, ubah nama file `.env.example` menjadi `.env`.
   - Sesuaikan konfigurasi database (username, password) dan atur `SECRET_KEY` dengan string acak.

3. **Install Dependensi**
   - Buka terminal di dalam folder utama proyek.
   - Jalankan perintah: `pip install -r requirements.txt`

4. **Jalankan Aplikasi**
   - Di terminal, jalankan: `python app.py`
   - Buka peramban (browser) dan akses: `http://127.0.0.1:5000`

---
*Proyek ini telah melalui proses Audit Keamanan dan Quality Assurance menyeluruh.*
