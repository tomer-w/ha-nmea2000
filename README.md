# 🚢 ha-nmea2000

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0)

> Transform your boat's NMEA 2000 network into powerful Home Assistant sensors instantly!

A Home Assistant integration that brings marine data to your smart home. Automatically detect and convert NMEA 2000 messages into Home Assistant sensors with zero configuration. Works with both USB and TCP CAN bus gateways. Based on pure Python NMEA 2000 [package](https://pypi.org/project/nmea2000/) built over [canboat](https://github.com/canboat/canboat) database.

## ✨ Features

- **Plug & Play** - Automatic sensor creation from detected messages
- **USB gateways**: CANBUS USB devices like [Waveshare USB-CAN-A](https://www.waveshare.com/wiki/USB-CAN-A)
- **TCP gateways**: CANBUS TCP devices like [ECAN-W01S](https://www.cdebyte.com/products/ECAN-W01S) or [ECAN-E01](https://www.cdebyte.com/products/ECAN-E01)
- **Real-time Data** - Instant marine metrics in your Home Assistant dashboard
- **Low Resource Usage** - Optimized performance with minimal overhead
- **Marine-focused** - Specially designed for boating enthusiasts

## 🔧 Installation

### Prerequisites
- A working Home Assistant installation
- NMEA 2000 network with compatible gateway (USB or TCP)

### Quick Start
1. **Install Gateway**: Connect and configure your NMEA 2000 gateway device
2. **Add Integration**: Install via HACS (Home Assistant Community Store)

# Acknowledgements

- This library leverages the [canboat](https://github.com/canboat/canboat) via [nmea2000](https://github.com/tomer-w/nmea2000) as the source for all PGN data.
- Special thanks to Rob from [Smart Boat Innovations](https://github.com/SmartBoatInnovations/). His code was the initial inspiration for this project. Some the code here might still be based on his latest OSS version.
