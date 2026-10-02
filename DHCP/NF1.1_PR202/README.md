# Monitorització DHCP amb Grafana - Comandes

**Shaila Martínez - 2n ASIX**

**Nº 63 - Serveis**

## Part 1: Exportador de Mètriques Kea

```bash
sudo apt install -y pipx
pipx ensurepath
source ~/.bashrc
```
Instal·lo pipx i recarrego el PATH per poder executar paquets Python sense tocar el del sistema.

```bash
pipx install kea-exporter
kea-exporter --version
```
Instal·lo l'exportador que tradueix les estadístiques de Kea a format Prometheus.

```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{"command": "statistic-get-all", "service": ["dhcp4"]}' \
     http://172.24.63.10:8000/
```
Comprovo que l'API de Kea respon abans de continuar.

```bash
which kea-exporter
```
Localitzo la ruta de l'executable, necessària per al servei systemd.

```bash
sudo nano /etc/systemd/system/kea-exporter.service
sudo systemctl daemon-reload
sudo systemctl enable --now kea-exporter
sudo systemctl status kea-exporter
```
Creo i activo el servei perquè kea-exporter s'executi sempre en segon pla.

```bash
curl http://172.24.63.10:9547/metrics | grep kea_dhcp4_addresses
```
Comprovo que les mètriques surten correctament.

## Part 2: Stack de Monitorització amb Docker

```bash
sudo apt-get remove docker docker-engine docker.io containerd runc
sudo apt-get install ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
Instal·lo Docker.

```bash
sudo docker --version
sudo docker compose version
sudo docker run hello-world
```
Comprovo que Docker funciona.

```bash
sudo usermod -aG docker $USER
exit
```
Per poder utilitzar Docker sense sudo.

```bash
mkdir -p ~/dhcp-monitoring-shailamartinez/prometheus
cd ~/dhcp-monitoring-shailamartinez
nano prometheus/prometheus.yml
```
Creo l'estructura del projecte i configuro Prometheus amb els dos jobs (kea-dhcp i rogue-detector).

```bash
nano prometheus/alert-rules.yml
```
Creo el fitxer buit abans d'aixecar Docker, perquè si no existeix el bind mount el crea com a directori i Prometheus falla.

```bash
nano docker-compose.yml
```
Defineixo els serveis prometheus i grafana.

```bash
docker compose up -d
docker compose ps
```
Aixeco l'stack i comprovo que els dos contenidors estan Up.

```bash
docker exec prometheus-shailamartinez wget -qO- http://172.24.63.10:9547/metrics | grep kea_dhcp4_addresses
```
Comprovo connectivitat des de dins del contenidor de Prometheus.

## Part 3: Dashboard de Grafana i Alerta d'Esgotament de Pool

Accedeixo per web a `http://localhost:3000`, afegeixo Prometheus com a datasource amb `http://prometheus:9090`.

```bash
mkdir -p grafana/provisioning/datasources grafana/provisioning/dashboards grafana/dashboards
nano grafana/provisioning/datasources/prometheus.yml
nano grafana/provisioning/dashboards/provider.yml
nano grafana/dashboards/dhcp.json
```
Implemento provisioning perquè Grafana carregui el datasource i el dashboard sols, sense fer-ho manualment des de la interfície.

```bash
nano docker-compose.yml
docker compose down
docker compose up -d
```
Munto els directoris de provisioning com a volums i reinicio l'stack perquè carregui la nova configuració.

```bash
tree
```
Comprovo l'estructura final de fitxers.

```bash
sudo nano /etc/systemd/system/rogue-detector.service
sudo systemctl daemon-reload
sudo systemctl enable --now rogue-detector
```
Creo per avançat el servei del detector de rogue DHCP.

```bash
nano prometheus/alert-rules.yml
docker compose restart prometheus
```
Afegeixo la regla DHCPPoolExhaustionWarning (90%) i la recarrego.

Comprovo a `http://localhost:9090/alerts` que la regla apareix en Inactive.

## Part 4: Detector de Servidors DHCP No Autoritzats

```bash
sudo apt install -y python3-prometheus-client
```
Instal·lo la llibreria amb apt perquè l'script en fa un import directe.

```bash
sudo nano /usr/local/bin/detect_rogue_dhcp.py
```
Creo l'script adaptant la IP legítima i la interfície real.

```bash
sudo systemctl start rogue-detector
curl http://172.24.63.10:9101/metrics | grep dhcp_rogue
```
Activo el detector i comprovo que la mètrica val 0.

```bash
nano prometheus/alert-rules.yml
docker compose restart prometheus
```
Afegeixo la regla RogueDHCPServerDetected i recarrego Prometheus.

Comprovo a `/alerts` que les dues regles apareixen en Inactive.

## Part 5.1: Simulació de DHCP Starvation

```bash
sudo apt install -y python3-scapy
nano ~/starvation_test.py
```
Instal·lo scapy i creo l'script que fa el cicle DORA complet (no només DISCOVER) per 150 MACs falses.

```bash
sudo python3 ~/starvation_test.py
```
Executo l'atac. Resultat: 101/150 adreces obtingudes, esgotant el pool real.

Comprovo a `/alerts` que DHCPPoolExhaustionWarning passa a Firing i al dashboard que l'ocupació puja al 100%.

```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{"command": "lease4-wipe", "service": ["dhcp4"]}' \
     http://172.24.63.10:8000/
```
Netejo els leases un cop acabada la prova.

```bash
curl http://172.24.63.10:9547/metrics | grep kea_dhcp4_addresses_assigned_total
```
Comprovo que l'ocupació ha tornat a 0.

## Part 5.2: Simulació d'un Servidor DHCP No Autoritzat

```bash
sudo apt install -y dnsmasq
sudo nano /etc/dnsmasq.conf
sudo systemctl restart dnsmasq
sudo systemctl status dnsmasq
```
Instal·lo i configuro un segon servidor DHCP (rang diferent del de Kea) en una altra màquina de la mateixa xarxa.

```bash
sudo nmcli device disconnect enp0s3
sudo nmcli device connect enp0s3
```
Des d'un client forço una desconnexió i reconnexió perquè envii un nou DISCOVER.

```bash
curl http://172.24.63.10:9101/metrics | grep dhcp_rogue
sudo cat /var/log/dhcp-rogue.log
```
Comprovo que la mètrica ha canviat a 1 i que l'alerta s'ha registrat amb la IP del rogue.

Comprovo a `/alerts` que RogueDHCPServerDetected passa a Firing i al dashboard que surt "ROGUE DETECTAT".

```bash
sudo systemctl stop dnsmasq
sudo apt purge -y dnsmasq
sudo apt autoremove -y
```
Aturo i desinstal·lo el servidor rogue.