"""
AI Factory Plant Simulator
============================
Physics-based simulation of a liquid-cooled AI data center.
Replaces physical hardware for full end-to-end testing.

Architecture:
  Plant Simulator ←→ NATS ←→ OPC UA Bridges ←→ CODESYS (or Python logic)

Models:
  - GPU racks: heat generation based on workload profiles
  - CDU: heat exchanger, pump, valve, thermal mass
  - Cooling tower: ambient rejection, fan control
  - Power: utility feed, UPS, PDU metering
  - Environment: room temperature, humidity response
  - Faults: sensor failure, pump trip, leak injection
"""
