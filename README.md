# Z2M HA Descriptions

[![hacs_custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/v/release/dtrywets/z2m-ha-descriptions?sort=semver)](https://github.com/dtrywets/z2m-ha-descriptions/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Home-Assistant-Integration, die die **Nutzer-Beschreibung** aus Zigbee2MQTT (Z2M) auf die passenden MQTT-Geräte in Home Assistant spiegelt.

Zigbee2MQTT speichert pro Gerät ein frei editierbares `description`-Feld (Standort, Notiz, Montageort). Home Assistant übernimmt diesen Text bei MQTT Discovery **nicht**. Diese Integration legt pro Z2M-Gerät einen **Diagnostic-Sensor** an, der den Wert live synchron hält.

> **Getestet mit:** Home Assistant 2026.7.x, Zigbee2MQTT 2.12.x, MQTT v5

---

## Inhaltsverzeichnis

- [Features](#features)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Einrichtung](#einrichtung)
- [Konfigurationsoptionen](#konfigurationsoptionen)
- [Funktionsweise](#funktionsweise)
- [Entitäten](#entitäten)
- [Services](#services)
- [Diagnose](#diagnose)
- [Beispiele](#beispiele)
- [Fehlerbehebung](#fehlerbehebung)
- [Entwicklung](#entwicklung)
- [Lizenz](#lizenz)

---

## Features

- Abonniert das retained MQTT-Topic `{base_topic}/bridge/devices`
- Synchronisiert nur das **top-level** Z2M-Feld `description` (Nutzer-Notiz)
- Ordnet Geräte über die IEEE-Adresse dem bestehenden Z2M-MQTT-Device in HA zu
- Legt pro Gerät einen Diagnostic-Sensor am **gleichen** Device an (kein zweites Gerät)
- Debounced Updates (2 s), idempotent
- Pending-Queue für Geräte, die beim ersten Sync noch nicht in HA existieren
- Services zum manuellen Neu-Sync und zum Entfernen aller Sensoren
- Diagnose-Daten in der Integrations-UI
- Config Flow und Options Flow (kein YAML nötig)

**Nicht synchronisiert:** `definition.description` — das ist Produkttext aus dem Z2M-Converter und landet in HA bereits als Gerätemodell (`model`).

---

## Voraussetzungen

| Komponente | Anforderung |
|---|---|
| Home Assistant | 2024.1 oder neuer (entwickelt/getestet unter 2026.7) |
| [MQTT-Integration](https://www.home-assistant.io/integrations/mqtt/) | aktiv, verbunden mit dem gleichen Broker wie Z2M |
| [Zigbee2MQTT](https://www.zigbee2mqtt.io/) | `homeassistant.enabled: true`, MQTT Discovery aktiv |
| HACS | optional, für bequeme Installation |

Z2M-Geräte müssen in Home Assistant bereits über MQTT Discovery existieren (Identifier `mqtt` / `zigbee2mqtt_{ieee}`).

---

## Installation

### Über HACS (empfohlen)

1. HACS → **Integrationen** → **⋮** → **Custom repositories**
2. Repository-URL eintragen: `https://github.com/dtrywets/z2m-ha-descriptions`
3. Kategorie: **Integration**
4. Integration **Z2M HA Descriptions** installieren
5. Home Assistant **neu starten**

### Manuell

1. Ordner `custom_components/z2m_ha_descriptions` aus diesem Repository nach `config/custom_components/` kopieren:

   ```bash
   rsync -av custom_components/z2m_ha_descriptions/ /config/custom_components/z2m_ha_descriptions/
   ```

2. Home Assistant **neu starten**

> Nach Updates an der Custom Component ist ein **Neustart** von Home Assistant erforderlich. Ein Reload der Integration reicht für geänderte Python-Module nicht aus.

---

## Einrichtung

1. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
2. **Z2M HA Descriptions** suchen und auswählen
3. Formular ausfüllen:

   | Feld | Standard | Beschreibung |
   |---|---|---|
   | **MQTT-Basis-Topic** | `zigbee2mqtt` | Muss dem `mqtt.base_topic` in der Z2M-Konfiguration entsprechen |
   | **Leere Beschreibungen synchronisieren** | aus | Siehe [Konfigurationsoptionen](#konfigurationsoptionen) |

4. **Senden**

Die Integration startet sofort und verarbeitet das retained Topic `{base_topic}/bridge/devices`.

**Abbruch:** Wenn die MQTT-Integration noch nicht eingerichtet ist, bricht der Config Flow mit `mqtt_not_loaded` ab.

---

## Konfigurationsoptionen

Optionen können nachträglich unter **Geräte & Dienste** → **Z2M HA Descriptions** → **Konfigurieren** geändert werden.

### MQTT-Basis-Topic (`base_topic`)

MQTT-Präfix von Zigbee2MQTT. Typische Werte:

- `zigbee2mqtt` (Standard)
- ein custom topic, falls in Z2M `configuration.yaml` gesetzt

Die Integration abonniert:

- `{base_topic}/bridge/devices` (Subscribe, retained)
- `{base_topic}/bridge/request/devices` (Publish für manuellen Refresh)

### Leere Beschreibungen synchronisieren (`sync_empty`)

| Wert | Verhalten |
|---|---|
| **Aus** (Standard) | Geräte ohne `description` oder mit leerem String werden **ignoriert**; bestehende Sensoren für entfernte Beschreibungen werden gelöscht |
| **An** | Auch leere Beschreibungen erzeugen/aktualisieren einen Sensor (State leer oder `""`) |

---

## Funktionsweise

### Datenfluss

```
Z2M (devices.yaml / Frontend)
        │
        ▼
MQTT  {base_topic}/bridge/devices  (retained JSON-Array)
        │
        ├──► HA MQTT Discovery  →  Device Registry (name, model, …)
        │
        └──► z2m_ha_descriptions  →  sensor.*_description
```

### Mapping Z2M → Home Assistant

| Z2M-Feld | Home Assistant |
|---|---|
| `ieee_address` | Device-Identifier `("mqtt", "zigbee2mqtt_{ieee.lower()}")` |
| top-level `description` | State des Sensors `sensor.{slug}_description` |
| `friendly_name` | **nicht** geändert (bleibt Gerätename via Discovery) |
| `definition.description` | **ignoriert** (Produkttext → bereits `device.model`) |

### Übersprungene Geräte

Einträge mit `type` **Coordinator** oder **Bridge** werden nicht synchronisiert.

### Pending-Queue

Existiert ein Z2M-Gerät mit `description`, aber das passende HA-Device noch nicht (z. B. direkt nach Pairing), wird die IEEE-Adresse in eine Warteschlange gelegt. Bei Änderungen in der Device Registry wird erneut gematcht.

### Debouncing

Mehrere schnelle Updates auf `bridge/devices` werden 2 Sekunden zusammengefasst, bevor Entitäten erstellt oder aktualisiert werden.

---

## Entitäten

Pro Z2M-Gerät mit gesetzter `description` (und passendem HA-Device) entsteht **eine** Sensor-Entität:

| Eigenschaft | Wert |
|---|---|
| Domain | `sensor` |
| Name | `{Gerätename} Description` |
| `unique_id` | `z2m_desc_{ieee}` (lowercase) |
| `entity_category` | `diagnostic` |
| Icon | `mdi:label-outline` |
| Device | gleiches Z2M-MQTT-Device wie die übrigen Entitäten |
| State | Z2M-Nutzer-`description` |

### Beispiel

Z2M:

```json
{
  "ieee_address": "0xa4c138df78859a58",
  "friendly_name": "Präsenzmelder Einbau 1",
  "description": "KG Büro - Regal"
}
```

Home Assistant:

- Device: **Präsenzmelder Einbau 1**
- Entität: `sensor.prasenzmelder_einbau_1_description`
- State: `KG Büro - Regal`

---

## Services

Domain: `z2m_ha_descriptions`

### `z2m_ha_descriptions.sync_now`

Fordert bei Z2M eine frische Device-Liste an (`bridge/request/devices`) und verarbeitet den zuletzt empfangenen `bridge/devices`-Payload erneut.

**Parameter:** keine

```yaml
service: z2m_ha_descriptions.sync_now
```

Entwicklerwerkzeuge:

```yaml
# Entwicklerwerkzeuge → Dienste
service: z2m_ha_descriptions.sync_now
```

### `z2m_ha_descriptions.clear`

Entfernt **alle** von dieser Integration erzeugten Description-Sensoren und leert die Pending-Queue. Z2M-Geräte und übrige MQTT-Entitäten bleiben unberührt.

**Parameter:** keine

```yaml
service: z2m_ha_descriptions.clear
```

> Nach `clear` reicht ein Neustart der Integration oder `sync_now`, um die Sensoren aus dem retained MQTT-Payload neu anzulegen.

---

## Diagnose

**Einstellungen** → **Geräte & Dienste** → **Z2M HA Descriptions** → **⋮** → **Diagnose**

| Feld | Bedeutung |
|---|---|
| `base_topic` | Konfiguriertes MQTT-Basis-Topic |
| `devices_topic` | Vollständiges Subscribe-Topic |
| `synced_count` | Anzahl erfolgreich zugeordneter Beschreibungen beim letzten Lauf |
| `unmatched_count` | Z2M-Geräte mit Description, aber ohne passendes HA-Device |
| `last_sync` | ISO-Zeitstempel der letzten Verarbeitung |
| `pending_ieees` | IEEE-Adressen in der Warteschlange |
| `entity_count` | Anzahl verwalteter Description-Sensoren |

---

## Beispiele

### Template: Description eines Geräts auslesen

```jinja2
{{ states('sensor.prasenzmelder_einbau_1_description') }}
```

### Automation: bei geänderter Description benachrichtigen

```yaml
automation:
  - alias: Z2M Description geändert
    trigger:
      - platform: state
        entity_id: sensor.prasenzmelder_einbau_1_description
    action:
      - service: notify.mobile_app_iphone
        data:
          message: "Neue Geräte-Notiz: {{ trigger.to_state.state }}"
```

### Alle Description-Sensoren finden

Entwicklerwerkzeuge → **Zustände**, Filter `description`, oder:

```yaml
{{ states.sensor
   | selectattr('entity_id', 'search', '_description')
   | map(attribute='entity_id') | list }}
```

### Description in Z2M pflegen

In `configuration.yaml` von Zigbee2MQTT:

```yaml
devices:
  '0xa4c138df78859a58':
    friendly_name: Präsenzmelder Einbau 1
    description: KG Büro - Regal
```

Oder über das Z2M-Frontend unter **Gerät** → **Description**. Nach Speichern republisht Z2M `bridge/devices`; die Integration aktualisiert den Sensor automatisch.

---

## Fehlerbehebung

| Symptom | Mögliche Ursache | Lösung |
|---|---|---|
| Integration erscheint nicht | Custom Component nicht geladen | Pfad prüfen, HA **neu starten** |
| Config Flow: `mqtt_not_loaded` | MQTT-Integration fehlt | Zuerst MQTT einrichten |
| Keine Sensoren | Keine `description` in Z2M gesetzt | In Z2M Frontend oder `devices.yaml` pflegen |
| Keine Sensoren | Falscher `base_topic` | Option an Z2M `mqtt.base_topic` anpassen |
| `unmatched_count` > 0 | HA-Device existiert noch nicht | Warten bis MQTT Discovery fertig; ggf. `sync_now` |
| Sensor fehlt nach Pairing | Timing | Pending-Queue; nach Discovery automatisch oder `sync_now` |
| Alter State nach Z2M-Änderung | Debounce / retained | 2 s warten oder `sync_now` |
| Integration `setup_error` nach Update | Python-Module gecacht | HA **neu starten** (nicht nur Reload) |

### Logs

```text
Einstellungen → System → Protokolle → Filter: z2m_ha_descriptions
```

---

## Entwicklung

Repository lokal klonen und Tests ausführen:

```bash
git clone git@github.com:dtrywets/z2m-ha-descriptions.git
cd z2m-ha-descriptions
python -m venv .venv
source .venv/bin/activate
pip install pytest homeassistant
pytest tests/
```

Fixture-Daten: `tests/fixtures/bridge_devices.json`

Projekt über `z2m-ha-descriptions.code-workspace` öffnen (stabile Workspace-Identität für Cursor-Chats).

### Projektstruktur

```text
custom_components/z2m_ha_descriptions/
├── __init__.py          # Setup, Services, Diagnose
├── manifest.json
├── config_flow.py       # Config- und Options-Flow
├── coordinator.py       # MQTT, Debounce, Entity-Lifecycle
├── entity.py            # Diagnostic-Sensor
├── sensor.py            # Platform-Setup
├── mapper.py            # Parse/Mapping (ohne HA-Abhängigkeit)
├── const.py
├── services.yaml
├── strings.json
└── translations/
    ├── de.json
    └── en.json
```

---

## Lizenz

MIT — siehe [LICENSE](LICENSE) (falls vorhanden) bzw. Repository-Root.

## Support

- [Issues](https://github.com/dtrywets/z2m-ha-descriptions/issues)
- [Zigbee2MQTT Dokumentation](https://www.zigbee2mqtt.io/guide/configuration/devices.html)
