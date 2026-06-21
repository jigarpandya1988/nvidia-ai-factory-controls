import React from 'react';
import { StatusDot } from '../common/StatusDot';
import { useProcessStore } from '../../stores/useProcessStore';

interface Props { type: 'nats' | 'aws' | 'pump' | 'sensors' | 'leak' | 'epo'; }

export function InfraDetail({ type }: Props) {
  const data = useProcessStore(s => s.current);

  if (type === 'nats') return (
    <div className="space-y-3 text-xs">
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">NATS Server</div>
        <div><span className="text-gray-500">URL:</span> <span className="font-mono text-nvidia">nats://192.168.200.10:4222</span></div>
        <div><span className="text-gray-500">Version:</span> NATS 2.10</div>
        <div><span className="text-gray-500">JetStream:</span> Enabled (10GB disk)</div>
        <div><span className="text-gray-500">Leaf Node:</span> → AWS (TLS)</div>
        <div><span className="text-gray-500">Uptime:</span> 47d 12h 33m</div>
      </div>
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Connections</div>
        <StatusDot status="ok" label="bridge-power (192.168.100.10)" />
        <StatusDot status="ok" label="bridge-cooling (192.168.100.20)" />
        <StatusDot status="ok" label="bridge-environment (192.168.100.30)" />
        <StatusDot status="ok" label="bridge-safety (192.168.100.40)" />
        <StatusDot status="ok" label="aws-forwarder" />
        <StatusDot status="ok" label="scada-backend (this app)" />
      </div>
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Streams (JetStream)</div>
        <div className="flex justify-between py-0.5"><span>TELEMETRY</span><span className="text-gray-400">1.2M msgs | 840 MB</span></div>
        <div className="flex justify-between py-0.5"><span>ALARMS</span><span className="text-gray-400">347 msgs | 2 MB</span></div>
        <div className="flex justify-between py-0.5"><span>COMMANDS</span><span className="text-gray-400">12 pending</span></div>
        <div className="flex justify-between py-0.5"><span>STATUS</span><span className="text-gray-400">6 msgs (latest only)</span></div>
      </div>
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Performance</div>
        <div>Messages/sec: ~500</div>
        <div>Avg latency: 0.12 ms</div>
        <div>Memory: 48 MB / 256 MB</div>
        <div>Disk: 840 MB / 10 GB</div>
      </div>
    </div>
  );

  if (type === 'aws') return (
    <div className="space-y-3 text-xs">
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">AWS IoT Core</div>
        <div><span className="text-gray-500">Endpoint:</span> xxx.iot.us-west-2.amazonaws.com</div>
        <div><span className="text-gray-500">Protocol:</span> MQTT over TLS 1.3</div>
        <div><span className="text-gray-500">Auth:</span> X.509 Device Certificate</div>
        <div><span className="text-gray-500">Site ID:</span> us-west-01</div>
      </div>
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Data Pipeline</div>
        <StatusDot status="ok" label="IoT Core → Timestream (hot, 24h)" />
        <StatusDot status="ok" label="IoT Core → Firehose → S3 (cold, 7yr)" />
        <StatusDot status="ok" label="IoT Core → Lambda (alarms → SNS)" />
        <StatusDot status="ok" label="Leaf Node → NATS Cloud (bidirectional)" />
      </div>
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Cost (this month)</div>
        <div className="flex justify-between"><span>IoT Core messages</span><span>$4.20</span></div>
        <div className="flex justify-between"><span>Timestream</span><span>$38.50</span></div>
        <div className="flex justify-between"><span>S3 storage</span><span>$1.80</span></div>
        <div className="flex justify-between"><span>Lambda invocations</span><span>$0.40</span></div>
        <div className="flex justify-between font-semibold mt-1 pt-1 border-t border-surface-4"><span>Total</span><span className="text-nvidia">$44.90</span></div>
      </div>
    </div>
  );

  if (type === 'pump') return (
    <div className="space-y-3 text-xs">
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">CDU-01 Primary Pump</div>
        <div><span className="text-gray-500">Status:</span> <span className={data?.pump_running ? 'text-green-400' : 'text-red-400'}>{data?.pump_running ? '● RUNNING' : '○ STOPPED'}</span></div>
        <div><span className="text-gray-500">Speed:</span> {data?.pump_cmd.toFixed(1) ?? '--'}%</div>
        <div><span className="text-gray-500">Motor:</span> 15 kW, 3-phase, 380V</div>
        <div><span className="text-gray-500">VFD:</span> ABB ACS580, no fault</div>
        <div><span className="text-gray-500">Run Hours:</span> 1,247 h</div>
        <div><span className="text-gray-500">Starts:</span> 34</div>
      </div>
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Maintenance</div>
        <div>Next bearing service: 3,753 h remaining</div>
        <div>Vibration: 1.2 mm/s (OK, limit 4.5)</div>
        <div>Motor temp: 52°C (OK, limit 80°C)</div>
        <div>Current: {data ? (data.pump_cmd * 0.2).toFixed(1) : '--'} A (nominal 20A)</div>
      </div>
    </div>
  );

  if (type === 'sensors') return (
    <div className="space-y-3 text-xs">
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Sensor Validation Status</div>
        <StatusDot status={data?.sensor_valid ? 'ok' : 'fault'} label={`Supply Temp PT1000 — ${data?.sensor_valid ? 'Valid' : 'FAULT'}`} />
        <StatusDot status="ok" label="Return Temp PT1000 — Valid" />
        <StatusDot status="ok" label="Flow Meter (electromagnetic) — Valid" />
        <StatusDot status="ok" label="Diff Pressure (4-20mA) — Valid" />
      </div>
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Validation Pipeline</div>
        <div>✓ Range check (physical limits)</div>
        <div>✓ Rate-of-change (spike rejection)</div>
        <div>✓ Redundancy voting (dual sensors)</div>
        <div>✓ Frozen signal detection (stuck sensor)</div>
        <div>✓ Low-pass filtering (noise rejection)</div>
        <div className="mt-1 text-gray-500">Fault threshold: 10 consecutive failures</div>
      </div>
    </div>
  );

  if (type === 'leak') return (
    <div className="space-y-3 text-xs">
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Leak Detection System</div>
        <div><span className="text-gray-500">Status:</span> <span className={data?.leak ? 'text-red-400' : 'text-green-400'}>{data?.leak ? '⚠ LEAK DETECTED' : '● ALL DRY'}</span></div>
        <div><span className="text-gray-500">Zones:</span> 16 sensing cable zones</div>
        <div><span className="text-gray-500">Debounce:</span> 500ms confirmation</div>
        <div><span className="text-gray-500">Classification:</span> Minor (1 zone) / Major (2+ zones)</div>
      </div>
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Zone Map</div>
        <div className="grid grid-cols-8 gap-1">
          {Array.from({length:16}, (_,i) => (
            <div key={i} className={`text-center py-1 rounded text-[9px] ${data?.leak && i === 0 ? 'bg-red-500/30 text-red-300 border border-red-500' : 'bg-green-500/10 text-green-400 border border-green-500/20'}`}>
              {i+1}
            </div>
          ))}
        </div>
      </div>
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Response Actions</div>
        <div>Minor: Alarm + isolate affected zone valve</div>
        <div>Major: Alarm + trip request to EPO controller</div>
        <div>Critical zone (under PDU): immediate trip</div>
      </div>
    </div>
  );

  if (type === 'epo') return (
    <div className="space-y-3 text-xs">
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Emergency Power Off System</div>
        <div><span className="text-gray-500">Status:</span> <span className="text-green-400">● ARMED</span></div>
        <div><span className="text-gray-500">Safety Level:</span> SIL 2 (IEC 61508)</div>
        <div><span className="text-gray-500">Response Time:</span> &lt; 100 ms</div>
        <div><span className="text-gray-500">Zones:</span> 8 independent zones</div>
        <div><span className="text-gray-500">Inputs:</span> Dual-channel (NC contacts)</div>
      </div>
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Trip Sources</div>
        <StatusDot status="ok" label="Manual pushbuttons (8) — No press" />
        <StatusDot status="ok" label="Fire detection — Normal" />
        <StatusDot status="ok" label="Major leak — No leak" />
        <StatusDot status="ok" label="Seismic sensor — Below threshold" />
        <StatusDot status="ok" label="Thermal runaway — Not detected" />
      </div>
      <div className="bg-surface-3 rounded p-3 border border-surface-4">
        <div className="text-gray-500 mb-2">Reset Requirements</div>
        <div>1. Physical key switch (maintained)</div>
        <div>2. Reset pushbutton (hold 3 seconds)</div>
        <div>3. Access control authorization</div>
        <div className="mt-1 text-yellow-400">Software-only reset is FORBIDDEN</div>
      </div>
    </div>
  );

  return <div>Unknown type</div>;
}
