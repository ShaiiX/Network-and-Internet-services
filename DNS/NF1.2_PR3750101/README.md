# Servidor DNS Autoritatiu, Recursiu i Segur amb BIND9

**Shaila Martínez - 2n ASIX**

**Nº 63 - Serveis**

Master 172.24.63.10, Slave 172.24.63.11

## Part 1: Instal·lació de BIND9

```bash
sudo apt update
sudo apt install -y bind9 bind9utils bind9-doc dnsutils
sudo hostnamectl set-hostname dns-master-shailamartinez
sudo hostnamectl set-hostname dns-slave-shailamartinez
sudo nano /etc/default/named
sudo systemctl restart bind9
sudo systemctl status bind9
```
Instal·lo BIND als dos servidors i canvio el hostname de cada un. A `/etc/default/named` poso `-4` perquè només faci servir IPv4. Comprovo que està `active (running)`.

## Part 2: Mode Cache/Recursiu i Forwarder

```bash
sudo nano /etc/bind/named.conf.options
sudo named-checkconf
sudo systemctl restart bind9
dig @172.24.63.10 www.google.com A
```
Al master activo la recursió només per a `172.24.63.0/24` i poso els reenviadors `192.168.88.107`, `8.8.8.8` i `1.1.1.1` amb `forward first`. Faig dos `dig` seguits: el primer tarda 23 msec i el segon 4 msec, perquè ja està a la memòria cau.

## Part 3: Zona Autoritativa Directa i Inversa

```bash
sudo nano /etc/bind/named.conf.local
sudo mkdir -p /etc/bind/zones
sudo nano /etc/bind/zones/db.shailamartinez.local
sudo nano /etc/bind/zones/db.172.24.63
sudo named-checkzone shailamartinez.local /etc/bind/zones/db.shailamartinez.local
sudo named-checkzone 63.24.172.in-addr.arpa /etc/bind/zones/db.172.24.63
sudo systemctl restart bind9
dig @172.24.63.10 www.shailamartinez.local
dig @172.24.63.10 -x 172.24.63.20
```
Creo la zona directa `shailamartinez.local` i la inversa, amb serial `2026101301` i TTL 604800. Valido les dues zones i comprovo amb `dig` que resolen i surt el flag `aa`.

## Part 4: Transferència de Zona Segura amb TSIG

```bash
tsig-keygen -a hmac-sha256 transfer-key | sudo tee /etc/bind/tsig.key
sudo scp /etc/bind/tsig.key smartinez6@172.24.63.11:/tmp/tsig.key
sudo nano /etc/bind/named.conf.options
sudo nano /etc/bind/named.conf.local
sudo named-checkconf
```
Genero la clau al master i la copio a l'slave. Poso `include "/etc/bind/tsig.key";` als dos servidors. Al master, la zona només deixa transferir amb la clau, i a l'slave la defineixo com a `slave` amb la clau.

```bash
sudo systemctl restart bind9
sudo rndc retransfer shailamartinez.local
dig @172.24.63.11 www.shailamartinez.local
dig @172.24.63.10 shailamartinez.local AXFR
```
Reinicio i forço la transferència a l'slave, que respon igual que el master. Des d'un client sense clau, l'AXFR dona `Transfer failed`.

## Part 5: Hardenització Bàsica

```bash
sudo nano /etc/bind/named.conf.options
sudo mkdir -p /var/log/bind
sudo chown bind:bind /var/log/bind
sudo systemctl restart bind9
dig @172.24.63.10 version.bind txt chaos
sudo tail -n 10 /var/log/bind/query.log
```
Poso `version "No disponible"`, `allow-query-cache`, `rate-limit` (15 respostes per segon) i el log de consultes. Comprovo la versió abans i després i que el log guarda consultes reals.

## Errors:

* BIND no arrencava en activar el log perquè AppArmor bloquejava `/var/log/bind/`: he afegit la regla `/var/log/bind/query.log rw,` a `/etc/apparmor.d/local/usr.sbin.named`, he recarregat AppArmor i he reiniciat.

* Els reenviadors `8.8.8.8` i `1.1.1.1` no funcionaven des de la xarxa del laboratori: he afegit `192.168.88.107` i he deixat `forward first`, així si cap respon BIND resol per ell mateix.

* Avisos `network unreachable` i `Unable to fetch DNSKEY`: BIND provava IPv6. Amb `-4` a `/etc/default/named` ja no surten.
