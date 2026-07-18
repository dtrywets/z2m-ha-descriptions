# Z2M HA Descriptions

Home-Assistant-Integration, die die **Nutzer-Beschreibung** aus dem Zigbee2MQTT-Topic `{base_topic}/bridge/devices` auf die passenden MQTT-Geräte in Home Assistant spiegelt.

## Hintergrund

Zigbee2MQTT speichert pro Gerät ein top-level `description`-Feld (frei editierbar, z. B. über die Z2M-Frontend-Oberfläche). Home Assistant zeigt diesen Text standardmäßig nicht als eigene Entität an. Diese Integration legt dafür einen **Diagnostic-Sensor** am bestehenden Z2M-MQTT-Gerät an.

**Nicht synchronisiert** wird `definition.description` — das ist Produkttext und landet ohnehin im Gerätemodell.

## Mapping

| Z2M | Home Assistant |
|-----|----------------|
| `ieee_address` | Device-Identifier `("mqtt", "zigbee2mqtt_{ieee.lower()}")` |
| top-level `description` | State des Sensors `sensor.*_description` |

Coordinator- und Bridge-Einträge werden übersprungen.

## Installation

### HACS (empfohlen)

1. Repository als Custom Repository hinzufügen
2. Integration installieren
3. Home Assistant neu starten

### Manuell

Den Ordner `custom_components/z2m_ha_descriptions` nach `config/custom_components/` kopieren und Home Assistant neu starten.

## Einrichtung

1. MQTT-Integration muss bereits eingerichtet sein
2. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Z2M HA Descriptions**
3. Optionen:
   - **MQTT-Basis-Topic** (Standard: `zigbee2mqtt`)
   - **Leere Beschreibungen synchronisieren** (Standard: aus)

Die Integration abonniert `{base_topic}/bridge/devices` (retained) und erzeugt pro passendem Gerät einen Sensor:

- `unique_id`: `z2m_desc_{ieee}`
- Kategorie: `diagnostic`
- hängt am bestehenden Z2M-MQTT-Device

Geräte, die beim ersten MQTT-Payload noch nicht in HA existieren, landen in einer **Pending-Queue** und werden bei Device-Registry-Updates erneut versucht.

## Services

| Service | Beschreibung |
|---------|--------------|
| `z2m_ha_descriptions.sync_now` | Fordert `bridge/request/devices` an und verarbeitet den Payload erneut |
| `z2m_ha_descriptions.clear` | Entfernt alle von der Integration erzeugten Beschreibungs-Sensoren |

## Diagnose

Unter **Integration → Z2M HA Descriptions → Diagnose** sind u. a. verfügbar:

- `synced_count` — zuletzt erfolgreich zugeordnete Beschreibungen
- `unmatched_count` — Geräte ohne passendes HA-Device
- `last_sync` — Zeitpunkt der letzten Verarbeitung
- `pending_ieees` — IEEE-Adressen in der Warteschlange

## Entwicklung

```bash
pytest tests/
```

Fixture-Daten in `tests/fixtures/bridge_devices.json` basieren auf:

- `0xa4c138df78859a58` → „KG Büro - Regal“
- `0xa4c138bcdad2d1d0` → „Whirlpool“

## Lizenz

MIT
