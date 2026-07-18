"""Constants for the Z2M HA Descriptions integration."""

DOMAIN = "z2m_ha_descriptions"

CONF_BASE_TOPIC = "base_topic"
CONF_SYNC_EMPTY = "sync_empty"

DEFAULT_BASE_TOPIC = "zigbee2mqtt"
DEFAULT_SYNC_EMPTY = False

MQTT_DOMAIN = "mqtt"
Z2M_DEVICE_ID_PREFIX = "zigbee2mqtt_"

ENTITY_UNIQUE_ID_PREFIX = "z2m_desc_"

TOPIC_BRIDGE_DEVICES_SUFFIX = "bridge/devices"
TOPIC_BRIDGE_REQUEST_DEVICES_SUFFIX = "bridge/request/devices"

DEBOUNCE_COOLDOWN = 2.0

ATTR_SYNCED_COUNT = "synced_count"
ATTR_UNMATCHED_COUNT = "unmatched_count"
ATTR_LAST_SYNC = "last_sync"

SERVICE_SYNC_NOW = "sync_now"
SERVICE_CLEAR = "clear"

SKIP_DEVICE_TYPES = frozenset({"Coordinator", "Bridge"})
