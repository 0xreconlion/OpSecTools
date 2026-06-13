"""Pi Telemetry – Lightweight Raspberry Pi hardware telemetry dashboard.

A self-contained browser dashboard for real-time monitoring of CPU, temperature,
memory, disk, network, and process metrics on Raspberry Pi or any Linux system.

Usage:
    python -m pi_telemetry.dashboard [--host 127.0.0.1] [--port 8788]

Environment variables:
    PI_TELEMETRY_PORT – HTTP server port (default: 8788)
    PI_TELEMETRY_BIND – HTTP server bind address (default: 127.0.0.1)
    PI_TELEMETRY_URL – URL opened in browser (default: http://127.0.0.1:{PORT})
"""

__version__ = "1.0.0"
__author__ = "ReconLion"
__license__ = "MIT"

__all__ = ["__version__", "__author__", "__license__"]
