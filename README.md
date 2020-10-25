# homeassistant_hikvision
Native implementation of Hikvison cameras\NVRs integration which relies on Hikvision ISAPI

Configuration example

```yaml
hikvision_isapi:
  nvr:
    base_url: http://my_nvr.local
    username: !secret nvr_username
    password: !secret nvr_password
    default_recovery_period: 00:01:00
    channels:
      - id: 1
        entity_id: cam01
        name: 'Cam 01: Front Facade'
      - id: 2
        name: Cam 02
      - id: none
        name: NVR
    alerts:
      - type: LineCrossing
        channel: 1
        name: Front facade line crossing
      - type: Intrusion
        channel: 2
      - type: LineCrossing
        channel: 2
        name: Backyard door motion
```