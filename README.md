# homeassistant_hikvision
Native implementation of Hikvison cameras\NVRs integration which relies on Hikvision ISAPI

This integration connects hikvision devices via __local__ http xml api (ISAPI). While there is a
 [stock hikvision integration ](https://www.home-assistant.io/integrations/hikvision/) there are 
 some key differences you might concider before making a choice:
 
* Stability. The author of this library wasn't manage to make it work reliably at least with NVR MODEL_NAME_HERE
* Config Flow. This integration uses config flow so you could connect your devices and modify configuration settings without the need to reboot home assistant.
* Healthcheck alerts could trigger home assistant event which makes it easier to handle with automations.
* Status sensors. It could monitor NVR params e.g. CPU\Mem\Disk usage which could be handy for health monitoring.
* Multiple platforms. E.g. apart of watching alert stream this integration could discover and create camera entities. 

## Installation

TBD

## Configuration options

TBD

## Automation examples

### Healthchecks 

TBD

### Video Surveillance Alarms

TBD

## Notes for developers and contributor

In order to setup developer's environment it's recommended to do the following:

1. Setup home assistant dev instance localy and make sure you could run and debug it. If you don't have one follow this steps:
    
    1. Create new folder `mkdir hass-dev && cd hass-dev`
    1. Create virtual env `virtualenv venv`
    1. Create configuration file `touch configuration.yaml` and put minimal config there: 
       ```
       TBD MINIMAL CONFIG
       ```
    1. Run home assistant like this `TBD`. You could use your favourite IDE and debuger e.g. for PyCharm the configuration might look like this. 

2. Make sure you have a folder `custrom_components` at the same level you have your `configuration.yaml`. If not - create it `mkdir custrom_components`

3. Checkout this repository into __separate folder__ located **outside** of the `hass-dev` tree. 

4. Create a symlink to bind the main component folder to the `hass-dev/custom_components`

## Credits
Dmitry Berezovsky

## Disclaimer
This module is licensed under GPL v3. This means you are free to use it even in commercial projects.

The GPL license clearly explains that there is no warranty for this free software. Please see the included LICENSE file for details.