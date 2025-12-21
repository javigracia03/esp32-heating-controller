# ESP32 Heating Controller

ESP32-based smart heating controller with remote ON/OFF via web or mobile app.  
MVP project for home automation and safe boiler control using a relay.

---

## 🚀 Overview

This project allows you to control a home heating system (boiler) remotely using:
- an **ESP32** with a relay (hardware control),
- a **backend API / MQTT** (command bridge),
- and a **web app** (React).

The ESP32 is connected **in parallel** to an existing physical thermostat, so:
- the manual thermostat keeps working,
- the ESP32 can also request heating safely.

---

## ✨ Features

- 🔥 Remote ON/OFF control of heating
- 🛜 Wi-Fi connectivity with ESP32
- 🌐 Web UI
- 🧰 Simple MVP architecture
- 🛡️ Safe relay-based control (no direct voltage to ESP32)
- ♻️ Reversible installation (doesn’t break existing setup)

