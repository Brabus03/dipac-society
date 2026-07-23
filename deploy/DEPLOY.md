# Deploy DIPAC Society ke VPS

## 1. Sewa VPS

Pilih salah satu (harga & langkah setup mirip semua): DigitalOcean, Hetzner, Vultr, Linode.
- OS: **Ubuntu 24.04 LTS**
- Spek minimal: 1 vCPU / 1GB RAM sudah cukup untuk skala ini

## 2. Arahkan domain ke VPS

Di panel DNS domain Anda, buat record:
```
A    @    <IP_VPS_ANDA>
```
Tunggu propagasi DNS (biasanya beberapa menit - 1 jam).

## 3. Setup awal VPS

SSH ke VPS (`ssh root@<IP_VPS_ANDA>`), lalu jalankan:

```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip git ufw

# firewall: hanya izinkan SSH, HTTP, HTTPS
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable

# user khusus buat jalankan app (jangan pakai root)
adduser --disabled-password --gecos "" dipac
```

## 4. Upload project

Dari laptop Anda (bukan di VPS):
```bash
rsync -avz --exclude 'graphify-out' --exclude '_previous-flat-version' --exclude 'data/dipac.db' \
  "<path-project-lokal-anda>/" root@<IP_VPS_ANDA>:/opt/dipac-society/
```
(`data/dipac.db` sengaja di-exclude supaya VPS bikin database baru yang bersih - upload manual belakangan kalau mau bawa data yang sudah ada)

## 5. Install dependency & set kepemilikan file

Di VPS:
```bash
chown -R dipac:dipac /opt/dipac-society
cd /opt/dipac-society
pip3 install -r requirements.txt --break-system-packages
```

## 6. Jalankan sebagai service (systemd)

```bash
cp deploy/dipac.service /etc/systemd/system/dipac.service
systemctl daemon-reload
systemctl enable dipac
systemctl start dipac
systemctl status dipac   # pastikan "active (running)"
```

## 7. Pasang HTTPS otomatis (Caddy)

```bash
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install -y caddy

# edit deploy/Caddyfile dulu, ganti "your-domain.com" jadi domain asli Anda
cp /opt/dipac-society/deploy/Caddyfile /etc/caddy/Caddyfile
systemctl restart caddy
```

Caddy otomatis urus sertifikat HTTPS (Let's Encrypt) dan reverse-proxy semua traffic domain Anda ke app Python di port 8000 (yang tidak diekspos langsung ke internet).

## 8. WAJIB sebelum go-live

- **Ganti password admin default** lewat halaman **Account** di dashboard setelah login pertama kali, atau set `DIPAC_ADMIN_PASSWORD` di environment sebelum database pertama kali dibuat (lihat README).
- Cek `https://your-domain.com` sudah jalan dengan gembok HTTPS di browser
- Backup rutin `data/dipac.db` (misal cron job harian copy ke tempat lain)

## Update aplikasi nanti

```bash
# dari laptop
rsync -avz --exclude 'data/dipac.db' "<path-project-lokal-anda>/" root@<IP_VPS_ANDA>:/opt/dipac-society/
# di VPS
systemctl restart dipac
```
