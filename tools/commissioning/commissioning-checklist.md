# Commissioning Checklist — NVIDIA AI Factory Controls

## Pre-Commissioning

### Hardware Verification
- [ ] All IPCs powered and booting to Linux
- [ ] CODESYS runtime service running on each IPC
- [ ] EtherCAT bus scanned, all slaves detected
- [ ] Network connectivity verified (ping all IPCs from edge gateway)
- [ ] OPC UA servers accessible on port 4840
- [ ] Time synchronization verified (< 1ms between IPCs)
- [ ] UPS providing clean power to control cabinet

### Software Verification
- [ ] CODESYS projects downloaded to each IPC
- [ ] All function blocks compile without errors
- [ ] Task configuration matches design (cycle times, priorities)
- [ ] OPC UA information model published correctly
- [ ] Edge gateway Docker services running
- [ ] MQTT broker accepting connections
- [ ] InfluxDB receiving data
- [ ] Grafana dashboards loading

---

## IPC-01: Power Control Commissioning

### Sensor Calibration
- [ ] Voltage transducers calibrated (±0.5% accuracy)
- [ ] Current transformers verified (ratio, polarity)
- [ ] Energy meters communicating via Modbus
- [ ] UPS Modbus communication verified
- [ ] ATS position feedback correct

### Functional Tests
- [ ] PUE calculation matches manual calculation (±2%)
- [ ] Phase imbalance alarm triggers at >20%
- [ ] Voltage high/low alarms trigger at correct thresholds
- [ ] Frequency deviation alarm functional
- [ ] Energy accumulation incrementing correctly
- [ ] ATS transfer command functional (if applicable)
- [ ] Load shed sequence tested (simulated)

---

## IPC-02: Cooling Control Commissioning

### Sensor Calibration
- [ ] Temperature sensors calibrated (PT1000, ±0.3°C)
- [ ] Flow meters calibrated (±2% of reading)
- [ ] Pressure sensors calibrated (±0.5% FS)
- [ ] VFD speed reference verified (4-20mA → 0-100%)
- [ ] Valve position feedback verified (4-20mA → 0-100%)

### Control Loop Tuning
- [ ] Pump PID: Step response test completed
- [ ] Pump PID: Overshoot < 10%, settling time < 60s
- [ ] Valve PID: Step response test completed
- [ ] Valve PID: Overshoot < 15%, settling time < 90s
- [ ] Feedforward gain calibrated against GPU power
- [ ] Ramp rate verified (no water hammer)

### Functional Tests
- [ ] CDU startup sequence completes without fault
- [ ] CDU shutdown sequence (controlled ramp-down)
- [ ] Standby pump switchover (< 5 seconds)
- [ ] High temperature alarm triggers correctly
- [ ] Low flow alarm triggers correctly
- [ ] Leak detection → zone isolation verified
- [ ] Emergency mode (100% cooling) functional
- [ ] Economizer mode transition (if ambient permits)

### Performance Verification
- [ ] Supply temperature stable within ±1°C of setpoint
- [ ] Response to 50% load step: < 30s to 90% recovery
- [ ] No oscillation at steady state
- [ ] Pump energy < 2% of IT load

---

## IPC-03: Environment Monitoring Commissioning

### Sensor Verification
- [ ] Temperature sensors reading within ±1°C of reference
- [ ] Humidity sensors reading within ±3% RH of reference
- [ ] Dew point calculation verified against psychrometric chart
- [ ] Particle counter functional

### Alarm Tests
- [ ] High temperature alarm at correct threshold
- [ ] Low temperature alarm at correct threshold
- [ ] High humidity alarm functional
- [ ] Condensation risk alarm functional
- [ ] Sensor fault detection (disconnect sensor, verify alarm)

---

## IPC-04: Safety Systems Commissioning

### CRITICAL: Perform with qualified safety engineer present

### EPO System
- [ ] Each EPO button tested (both channels)
- [ ] Dual-channel monitoring: disconnect one wire → fault alarm
- [ ] EPO activation → power contactor opens (< 100ms)
- [ ] Zone isolation correct (only affected zone trips)
- [ ] Reset sequence: requires key + button + authorization
- [ ] Reset sequence: 3-second hold verified
- [ ] EPO relay fail-safe verified (de-energize to trip)

### Fire Detection
- [ ] VESDA alert level → alarm generated
- [ ] VESDA fire level → suppression countdown starts
- [ ] Spot detector → alarm generated
- [ ] Abort button stops countdown
- [ ] Suppression discharge valve operates (test with gas)
- [ ] Damper close command verified
- [ ] Evacuation alarm activates

### Leak Detection
- [ ] Each zone cable tested (apply water)
- [ ] Minor leak → alarm + zone isolation
- [ ] Major leak → EPO + full isolation
- [ ] Zone identification correct in alarm message

### Seismic
- [ ] Accelerometer calibration verified
- [ ] 0.1g threshold → warning alarm
- [ ] 0.3g threshold → controlled shutdown
- [ ] Pump stop and valve close verified

---

## Integration Tests

### Inter-IPC Communication
- [ ] IPC-02 reads GPU power from edge gateway (OPC UA)
- [ ] IPC-04 safety status visible to all other IPCs
- [ ] IPC-01 power data available to IPC-02 (coordination)
- [ ] All IPCs publishing to OPC UA aggregator

### Cloud Connectivity
- [ ] Sparkplug B bridge publishing to cloud MQTT
- [ ] Birth certificates sent on connection
- [ ] Death certificate (LWT) configured
- [ ] Store-and-forward: disconnect cloud, verify buffering
- [ ] Store-and-forward: reconnect, verify data delivery
- [ ] Grafana dashboards showing live data
- [ ] Alarm notifications reaching operators (email/SMS)

### End-to-End Scenarios
- [ ] **Scenario 1**: GPU load increase → cooling responds → temperature stable
- [ ] **Scenario 2**: Pump failure → standby switchover → no temperature excursion
- [ ] **Scenario 3**: Power loss → UPS holds → generator starts → transfer
- [ ] **Scenario 4**: Leak detected → zone isolated → alarm sent → operator responds
- [ ] **Scenario 5**: Fire detected → countdown → suppression (simulated)
- [ ] **Scenario 6**: Cloud disconnect → local operation continues → reconnect

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Controls Engineer | | | |
| Safety Engineer | | | |
| Mechanical Engineer | | | |
| Electrical Engineer | | | |
| Facility Manager | | | |
| NVIDIA Site Rep | | | |
