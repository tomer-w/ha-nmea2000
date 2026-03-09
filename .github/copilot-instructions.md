# Copilot Instructions for ha-nmea2000

## Project Overview

This is a Home Assistant custom integration for NMEA 2000 marine data. It connects to NMEA 2000 gateways (CAN, USB, TCP/EBYTE) and exposes PGN data as HA sensors.

## Project Structure

- `custom_components/nmea2000/` — Integration source code
  - `__init__.py` — Integration setup and entry points
  - `hub.py` — Gateway orchestration, sensor creation, PGN processing
  - `NMEA2000Sensor.py` — Sensor entity class
  - `config_flow.py` — Configuration UI flow
  - `const.py` — Constants and configuration keys
- `tests/` — Pytest test suite
- `.devcontainer/` — Dev container configuration for Linux-based development

## Key Dependencies

- `nmea2000` Python library (listed in `requirements.txt`)
- `pytest-homeassistant-custom-component` for testing (listed in `requirements_test.txt`)

## Testing

### Important: Tests require Linux

Tests depend on `pytest-homeassistant-custom-component` which requires Linux. They **cannot** run natively on Windows.

### Running tests

Always run tests in Docker using the devcontainer image:

```bash
cd C:\ttt\ha-nmea2000
docker run --rm -v "${PWD}:/workspace" -w /workspace mcr.microsoft.com/devcontainers/python:3.13 bash -c "pip install --quiet -r requirements.txt -r requirements_test.txt 2>&1 | tail -3 && pytest tests/ -v 2>&1"
```

### When to run tests

- **Always** run tests after making any code changes, before considering the task complete.
- Run tests before committing.

## CI/CD

- `.github/workflows/validate.yaml` — Runs HACS validation, hassfest, and pytest on push/PR.
- Tests in CI install both `requirements.txt` and `requirements_test.txt`.

## Code Conventions

- Entity ID sanitization (spaces, hyphens → underscores) happens in `NMEA2000Sensor.__init__`, not in the hub.
- `hub.py` passes raw names as `sensor_id` to `NMEA2000Sensor`; the sensor class handles all ID normalization.
- The `NMEA2000Sensor` constructor parameter is named `sensor_id` (not `id`).
- Use `pyproject.toml` for all project metadata (PEP 621). No `setup.py`.
