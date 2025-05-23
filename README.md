# 🚢 ha-nmea2000

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0)

> Transform your boat's NMEA 2000 network into powerful Home Assistant sensors instantly!

A Home Assistant integration that brings marine data to your smart home. Automatically detect and convert NMEA 2000 messages into Home Assistant sensors with zero configuration. Works with both USB and TCP CAN bus gateways. Based on pure Python NMEA 2000 [package](https://pypi.org/project/nmea2000/) built over [canboat](https://github.com/canboat/canboat) database.

## ✨ Features

- **Plug & Play** - Automatic sensor creation from detected messages
- **USB gateways**: CANBUS USB devices like [Waveshare USB-CAN-A](https://www.waveshare.com/wiki/USB-CAN-A)
- **TCP gateways**: CANBUS TCP devices like:
     - [EBYTE ECAN-W01S](https://www.cdebyte.com/products/ECAN-W01S)
     - [EBYTE ECAN-E01](https://www.cdebyte.com/products/ECAN-E01)
     - [Actisense W2K-1](https://actisense.com/products/w2k-1-nmea-2000-wifi-gateway/)
     - [Yacht Devices YDEN-02](https://yachtdevicesus.com/products/nmea-2000-ethernet-gateway-yden-02)
- **Real-time Data** - Instant marine metrics in your Home Assistant dashboard
- **Low Resource Usage** - Optimized performance with minimal overhead
- **Marine-focused** - Specially designed for boating enthusiasts

## 🔧 Installation

### Prerequisites
- A working Home Assistant installation
- NMEA 2000 network with compatible gateway (USB or TCP)


### 🛠 Option 1: Installation via HACS

To install this integration in Home Assistant using HACS:

1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Click the **⋮ menu** (top right) → **Custom repositories**.
4. Paste this repository URL:  
   `https://github.com/tomer-w/ha-nmea2000`
5. Set the category to **Integration** and click **Add**.
6. Search for **NMEA 2000** in HACS and install it. Or, press the link below:  
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tomer-w&repository=ha-nmea2000)  
7. Restart Home Assistant when prompted.  

### 🛠 Option 2: Manual Installation

1. Download the latest release ZIP file:  
   📦 [ha-nmea2000.zip](https://github.com/tomer-w/ha-nmea2000/releases/latest/download/ha-nmea2000.zip)
2. Extract the contents into your Home Assistant `custom_components` directory:

   ```bash
   mkdir -p /config/custom_components/nmea2000
   unzip ha-nmea2000.zip -d /config/custom_components/nmea2000
   ```
3. Restart Home Assistant.

### 🛠 Add the integration
1. Go to Settings → Devices & Services → + Add Integration and search for NMEA 2000. Or, press the link below:  
[![Open your Home Assistant instance and show an integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=nmea2000)
2. Click the **ADD HUB** button
3. Choose a name and if the gateway is USB or TCP one.
4. Based on the gateway type choose how to connect to it (USB port or TCP IP and port)
2. **Customize**: Choose what PGNs to monitor and in what cadance you want the updates

# Acknowledgements

- This library leverages the [canboat](https://github.com/canboat/canboat) via [nmea2000](https://github.com/tomer-w/nmea2000) as the source for all PGN data.
- Special thanks to Rob from [Smart Boat Innovations](https://github.com/SmartBoatInnovations/). His code was the initial inspiration for this project. Some the code here might still be based on his latest OSS version.
