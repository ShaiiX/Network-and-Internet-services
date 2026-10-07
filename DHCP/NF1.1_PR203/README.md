# Alta Disponibilitat de DHCP amb Kea (Hot-Standby) - Comandes

**Shaila Martínez - 2n ASIX**

**Nº 63 - Serveis**

Primari 172.24.63.10, Secundari 172.24.63.11

## Part 1: Preparació dels Dos Servidors

```bash
sudo hostnamectl set-hostname kea-server2-shailamartinez
sudo nano /etc/netplan/*.yaml
sudo netplan apply
```
Al clon canvio el hostname i la IP (172.24.63.11)

```bash
hostnamectl
ip a
sudo systemctl stop kea-dhcp4-server kea-ctrl-agent
systemctl status kea-dhcp4-server kea-ctrl-agent
```
Comprovo noms i IPss i aturo els serveis mentre configuro

## Part 2: Configuració Base Idèntica del Subnet

```bash
sudo nano /etc/kea/kea-dhcp4.conf
sudo nano /etc/kea/kea-ctrl-agent.conf
sudo systemctl restart kea-dhcp4-server kea-ctrl-agent
```
Poso la mateixa configuració als dos servidors i reinicio els serveis.

## Part 3: Configuració del Hook d'Alta Disponibilitat

```bash
sudo nano /etc/kea/kea-dhcp4.conf
sudo kea-dhcp4 -t /etc/kea/kea-dhcp4.conf
sudo systemctl restart kea-dhcp4-server
```
Afegeixo `hooks-libraries` només canvia `this-server-name`, valido la sintaxi i reinicio.

```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{"command": "status-get", "service": ["dhcp4"]}' \
     http://172.24.63.10:8000/
```
Comprovo l'estat del HA al secundari, amb `172.24.63.11`. Passa de `waiting` i `syncing` a `hot-standby`.

## Part 4: Failover i Failback

```bash
sudo dhclient -r enp0s3
sudo dhclient enp0s3
ip a show enp0s3
```
Des del client demano una concessió

```bash
sudo systemctl stop kea-dhcp4-server
curl -s -X POST -H "Content-Type: application/json" \
     -d '{"command": "status-get", "service": ["dhcp4"]}' \
     http://172.24.63.11:8000/
```
Paro el primari i comprovo que el secundari pasa a `partner-down`, el client segueix obtenint IP

```bash
sudo systemctl start kea-dhcp4-server
```
Arrenco el primari i comprovo amb `status-get` que els dos tornen a `hot-standby`.

## Errors:

* La llibreria no estava a `/usr/lib/kea/hooks/` i he posat la ruta `/usr/lib/x86_64-linux-gnu/kea/hooks/libdhcp_ha.so`

* El socket no estava a `/tmp/`: he posat `/run/kea/kea4-ctrl-socket` a `kea-dhcp4.conf` i a `kea-ctrl-agent.conf` (explicat a la Pr1 també)

* Error `Address already in use`: he desactivat el multi-threading i els listeners HTTP de l'HA, perquè entraven en conflicte amb `kea-ctrl-agent`

  * `enable-multi-threading: false`: desactiva el multi-threading de l'HA
  * `http-dedicated-listener: false`: evita que l'HA crei un listener HTTP propi
  * `http-listener-threads: 0`: no crea fils per al listener HTTP de l'HA.
  * `http-client-threads: 0`: no crea fils addicionals per a les connexions HTTP
  * Ho he posat per evitar conflictes amb `kea-ctrl-agent`, que ja utilitza el port `8000`. També es podria haver utilitzat un altre port, però he mantingut el 8000, ja que d'aquesta manera es manté la configuració en els dos servidors canviant només la IP.

* Error `lease4-get-page command not supported`: he afegit la llibreria `libdhcp_lease_cmds.so` als dos servidors. Aquesta llibreria permet utilitzar les comandes per consultar i gestionar els leases, perquè l'HA pugui sincronitzar els leases entre els dos servidors

* El primari es quedava en `syncing` al failback: he afegit `libdhcp_lease_cmds.so` i he reiniciat el servei perquè es sincronitzessin els leases

