# Servei DHCP amb Kea

**Serveis 2n ASIX**   
**Shaila Martínez**  
**Número de llista: 63**  

---

## Paràmetres xarxa

| Paràmetre | Valor Assignat |
| :--- | :--- |
| **Subxarxa** | `172.24.63.0/24` |
| **IP server kea** | `172.24.63.10` |
| **Pool dinàmic DHCP** | `172.24.63.100` - `172.24.63.200` |
| **Reserves estàtiques MAC** | `172.24.63.50`, `172.24.63.51`, `172.24.63.52` |
| **Gateway** | `172.24.63.1` |
| **DNS** | `172.24.63.10`, `8.8.8.8` |
| **Domini** | `shailamartinez.local` |
| **NTP** | `172.24.63.1` |

---

## Estructura

### 1. Configuració netplan
Fitxer `/etc/netplan/00-installer-config.yaml`:

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: false
      dhcp6: false
      addresses: [172.24.63.10/24]
```

Aplicar els canvis:

```bash
sudo netplan apply
```

### 2. Instal·lació dels paquets
A Ubuntu Server 26.04 s'instal·len els components natius de Kea:

```bash
sudo apt update
sudo apt install -y kea-dhcp4-server kea-ctrl-agent kea-common
```

### 3. Configuració server kea-dhcp4.conf
Configuració en format JSON:

```json
{
  "Dhcp4": {
    "interfaces-config": {
      "interfaces": [ "enp0s3" ]
    },
    "lease-database": {
      "type": "memfile",
      "persist": true,
      "name": "/var/lib/kea/kea-leases4.csv"
    },
    "valid-lifetime": 3600,
    "renew-timer": 1800,
    "rebind-timer": 3150,
    "hooks-libraries": [
      {
        "library": "/usr/lib/x86_64-linux-gnu/kea/hooks/libdhcp_lease_cmds.so"
      }
    ],
    "subnet4": [
      {
        "id": 1,
        "subnet": "172.24.63.0/24",
        "pools": [ { "pool": "172.24.63.100 - 172.24.63.200" } ],
        "reservations": [
          {
            "hw-address": "08:00:27:11:22:33",
            "ip-address": "172.24.63.50",
            "hostname": "servidor-impressio-shailamartinez"
          },
          {
            "hw-address": "08:00:27:44:55:66",
            "ip-address": "172.24.63.51",
            "hostname": "pc-direccio-shailamartinez"
          },
          {
            "hw-address": "08:00:27:77:88:99",
            "ip-address": "172.24.63.52",
            "hostname": "servidor-backup-shailamartinez"
          }
        ],
        "option-data": [
          { "name": "routers", "data": "172.24.63.1" },
          { "name": "domain-name-servers", "data": "172.24.63.10, 8.8.8.8" },
          { "name": "domain-name", "data": "shailamartinez.local" },
          { "name": "ntp-servers", "data": "172.24.63.1" }
        ]
      }
    ],
    "control-socket": {
      "socket-type": "unix",
      "socket-name": "/run/kea/kea4-ctrl-socket"
    },
    "loggers": [
      {
        "name": "kea-dhcp4",
        "output-options": [ { "output": "/var/log/kea/kea-dhcp4.log" } ],
        "severity": "INFO"
      }
    ]
  }
}
```

**Configuració addicional indicada:**

- He afegir la llibreria "hooks" perquè al fer `curl` al servidor, retornava error `command not supported`. Ja que Kea no permet 
gestionar concessions mitjançant API REST per defecte.

- Rutes del socket de control i registres: `/run/kea/kea4-ctrl-socket` i `/var/log/kea/kea-dhcp4.log` s'utilitzen les rutes natives que crea el paquet oficial d'Ubuntu al instal·lar-se. `/run/kea` és la ubicació estàndard i segura per sockets de serveis. `/var/log/kea/` manté els logs dins del seu propi directori.


### 4. Configuració agent de control REST kea-ctrl-agent.conf
Paràmetres del agent HTTP:

```json
{
  "Control-agent": {
    "http-host": "0.0.0.0",
    "http-port": 8000,
    "control-sockets": {
      "dhcp4": {
        "socket-type": "unix",
        "socket-name": "/run/kea/kea4-ctrl-socket"
      }
    },
    "loggers": [
      {
        "name": "kea-ctrl-agent",
        "output-options": [ { "output": "/var/log/kea/kea-ctrl-agent.log" } ],
        "severity": "INFO"
      }
    ]
  }
}
```

**Configuració addicional indicada:**

- Ruta del socket de control: socket-name `/run/kea/kea4-ctrl-socket` la ruta definida ha de coincidir amb la configurada en `kea-dhcp4.conf` per podder communicar-se.

- Bloc de registres (loggers) per tenir un registre independent de les peticions que reb l'agent REST HTTP. Al fer les proves amb `curl`, si donava un error, tenir els logs guardats en `/var/log/kea/kea-ctrl-agent.log` permet verificar que les peticions HTTP han entrar i indicat les fallades sense dependre del journalctl.


---

## Comandes de comprovació

**Validació de sintaxi fitxer JSON:**
```bash
sudo kea-dhcp4 -t /etc/kea/kea-dhcp4.conf
```

**Reinici i estat dels serveis**
```bash
sudo systemctl restart kea-dhcp4-server kea-ctrl-agent
sudo systemctl status kea-dhcp4-server kea-ctrl-agent
```

**Eestat via API RESt (status-get):**
```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{"command": "status-get", "service": ["dhcp4"]}' \
```

**Configuració (API REST config-get):**
```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{"command": "config-get", "service": ["dhcp4"]}' \
```

**Fitxer de concessions:**
```bash
sudo cat /var/lib/kea/kea-leases4.csv
```

**Petició DHCP client:**
```bash
sudo dhclient -r eth0   # allibera la concessió actual
sudo dhclient eth0      # sol·licita una nova concessió
ip a show eth0
```

**Comprovació fitxer de concessions**
```
sudo cat /var/lib/kea/kea-leases4.csv
```

## Proves validacions clients

**Forçar targeta a quedar-se sense IP:**
```
ipconfig /release
```

**Assignar la IP reservada:**
```
ipconfig /renew
```

**Comprovar que rep IP:**
```
nmcli device show enp0s3
```

**Forçar la petició desconnectant i connectant la interfície:**
```
sudo nmcli device disconnect enp0s3
sudo nmcli device connect enp0s3
```

**Fitxer de concessió:**
```
sudo cat /var/lib/dhcp/dhclient.leases
```

