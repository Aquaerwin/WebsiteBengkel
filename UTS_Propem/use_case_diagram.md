# Use Case Diagram - Website Bengkel (Sesuai Referensi <<include>>)

File ini berisi kode (*script*) untuk menghasilkan (me-render) gambar Use Case Diagram secara otomatis. Kode ini sudah **disesuaikan dengan gaya gambar referensi Anda**, yaitu:
1. **Admin berada di sebelah kiri** dan **Pelanggan di sebelah kanan**.
2. **Login berada di tengah** sebagai pusat.
3. Fitur-fitur utama menggunakan garis putus-putus **`<<include>>`** yang mengarah ke *Login* (menandakan bahwa untuk melakukan fitur tersebut, pengguna wajib *Login* terlebih dahulu).
4. Semua fitur lengkap Anda tidak ada yang dikurangi.

## Menggunakan PlantUML (Sangat Disarankan & Sesuai Referensi)
**Cara menggunakan:**
1. Buka situs web **[PlantText.com](https://www.planttext.com/)** atau **[PlantUML Web Server](http://www.plantuml.com/plantuml/uml/)**.
2. Salin (*copy*) semua teks di dalam kotak kode di bawah ini.
3. Tempel (*paste*) ke dalam kotak teks di situs web tersebut.
4. Klik tombol "Refresh" atau "Submit" untuk memunculkan gambarnya, lalu Anda bisa *Download* gambarnya (PNG).

```plantuml
@startuml
skinparam packageStyle rectangle
left to right direction

' Definisi Aktor (Admin kiri, Pelanggan Kanan)
actor "Admin" as admin
actor "Pelanggan" as pelanggan

' Batas Sistem
rectangle "Sistem Website Bengkel Mesin & Cat" {
    
    ' Pusat Login
    usecase "Login" as UC_Login
    usecase "Registrasi Akun" as UC_Reg
    
    ' Use case publik (Pelanggan, tidak butuh login)
    usecase "Melihat Profil & Layanan" as UC_Profil
    usecase "Melihat Galeri Portofolio" as UC_Galeri
    
    ' Use case Pelanggan yang butuh Login (<<include>>)
    usecase "Melakukan Booking Jadwal" as UC_Booking
    usecase "Memantau Status Booking" as UC_StatusBooking
    usecase "Membatalkan Booking" as UC_BatalBooking
    usecase "Mengelola Data Profil" as UC_KelolaProfil
    
    ' Use case Admin yang butuh Login (<<include>>)
    usecase "Kelola Data Layanan" as UC_KelolaLayanan
    usecase "Kelola Galeri Portofolio" as UC_KelolaGaleri
    usecase "Verifikasi & Konfirmasi Booking" as UC_Verifikasi
    usecase "Update Catatan Servis" as UC_UpdateServis

    ' Relasi Include ke arah Login (Garis putus-putus <<include>>)
    UC_Reg .> UC_Login : <<include>>
    UC_Booking .> UC_Login : <<include>>
    UC_StatusBooking .> UC_Login : <<include>>
    UC_BatalBooking .> UC_Login : <<include>>
    UC_KelolaProfil .> UC_Login : <<include>>
    
    UC_KelolaLayanan .> UC_Login : <<include>>
    UC_KelolaGaleri .> UC_Login : <<include>>
    UC_Verifikasi .> UC_Login : <<include>>
    UC_UpdateServis .> UC_Login : <<include>>
}

' Relasi Aktor Pelanggan (Garis Lurus)
UC_Reg -- pelanggan
UC_Login -- pelanggan
UC_Profil -- pelanggan
UC_Galeri -- pelanggan
UC_Booking -- pelanggan
UC_StatusBooking -- pelanggan
UC_BatalBooking -- pelanggan
UC_KelolaProfil -- pelanggan

' Relasi Aktor Admin (Garis Lurus)
admin -- UC_Login
admin -- UC_KelolaLayanan
admin -- UC_KelolaGaleri
admin -- UC_Verifikasi
admin -- UC_UpdateServis

@enduml
```

---

### Rangkuman Perubahan dari Versi Sebelumnya:
*   Sesuai dengan gambar referensi Anda, diagram ini sekarang menggunakan sistem ketergantungan **`<<include>>`** ke arah fitur *Login*.
*   Artinya, diagram ini secara otomatis menceritakan bahwa baik Pelanggan maupun Admin **harus melewati proses Login** sebelum bisa melakukan *Booking*, *Mengelola Profil*, atau *Memverifikasi Antrean*.
*   Aktor "Admin" sudah dipindah posisinya ke sebelah kiri, dan "Pelanggan" di sebelah kanan.
*   Bentuk *Use Case* (Oval) dan Aktor (*Stickman*) dipastikan akan muncul sempurna persis seperti gambar referensi Anda (tidak terputus-putus) jika Anda menjalankannya di PlantUML.
