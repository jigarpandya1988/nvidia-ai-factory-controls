# STATUS: SCAFFOLD — Production implementation requires AWS IoT SDK integration
"""
IPC Monitoring & Deployment Agent
===================================
Runs as a Docker container on each physical IPC alongside CODESYS.

Responsibilities:
  1. LOG SHIPPING — Tails CODESYS log files, sends to CloudWatch Logs
  2. RESOURCE MONITORING — CPU, RAM, disk, network → CloudWatch Metrics
  3. DEPLOYMENT AGENT — Listens for IoT Jobs, downloads & applies updates
  4. HEALTH HEARTBEAT — Publishes alive status to IoT Core every 30s

This agent is the ONLY component on the IPC that talks to AWS.
CODESYS itself is unaware of the cloud — clean separation of concerns.
"""

import asyncio
import json
import logging
import os
import signal
import time
from pathlib import Path

import psutil
import yaml

logger = logging.getLogger(__name__)

# Configuration from environment or config file
CONFIG = {
    'site_id': os.environ.get('SITE_ID', 'us-west-01'),
    'ipc_id': os.environ.get('IPC_ID', 'cooling'),
    'iot_endpoint': os.environ.get('IOT_ENDPOINT', ''),
    'cert_path': os.environ.get('CERT_PATH', '/opt/ipc-agent/certs/device.pem.crt'),
    'key_path': os.environ.get('KEY_PATH', '/opt/ipc-agent/certs/private.pem.key'),
    'ca_path': os.environ.get('CA_PATH', '/opt/ipc-agent/certs/AmazonRootCA1.pem'),
    'codesys_log_path': os.environ.get('CODESYS_LOG', '/var/log/codesyscontrol.log'),
    'codesys_project_path': os.environ.get('CODESYS_PROJECT', '/opt/codesys/project/'),
    'metric_interval_s': int(os.environ.get('METRIC_INTERVAL', '60')),
    'heartbeat_interval_s': int(os.environ.get('HEARTBEAT_INTERVAL', '30')),
    'log_group': '',  # Set dynamically
}


class ResourceMonitor:
    """Collects system resource metrics and publishes to CloudWatch."""

    def __init__(self, ipc_id: str, site_id: str):
        self.ipc_id = ipc_id
        self.site_id = site_id

    def collect(self) -> dict:
        """Collect current resource utilization."""
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()

        # CODESYS process-specific metrics
        codesys_proc = self._find_codesys_process()
        codesys_cpu = codesys_proc.cpu_percent() if codesys_proc else 0.0
        codesys_mem = codesys_proc.memory_percent() if codesys_proc else 0.0

        return {
            'timestamp': int(time.time() * 1000),
            'system': {
                'cpu_percent': cpu,
                'memory_percent': mem.percent,
                'memory_used_mb': mem.used / (1024 * 1024),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024 * 1024 * 1024),
                'net_bytes_sent': net.bytes_sent,
                'net_bytes_recv': net.bytes_recv,
            },
            'codesys': {
                'cpu_percent': codesys_cpu,
                'memory_percent': codesys_mem,
                'running': codesys_proc is not None,
            },
        }

    def _find_codesys_process(self):
        """Find the CODESYS runtime process."""
        for proc in psutil.process_iter(['name']):
            if 'codesyscontrol' in (proc.info['name'] or '').lower():
                return proc
        return None


class LogShipper:
    """Tails CODESYS log files and ships to CloudWatch."""

    def __init__(self, log_path: str, site_id: str, ipc_id: str):
        self.log_path = Path(log_path)
        self.site_id = site_id
        self.ipc_id = ipc_id
        self._last_position = 0

    async def tail_and_ship(self):
        """Continuously tail the log file and send new lines."""
        while True:
            try:
                if self.log_path.exists():
                    with open(self.log_path, 'r') as f:
                        f.seek(self._last_position)
                        new_lines = f.readlines()
                        self._last_position = f.tell()

                        if new_lines:
                            # In production: batch and send to CloudWatch Logs
                            # via boto3 put_log_events()
                            for line in new_lines:
                                logger.debug(f"[CODESYS] {line.strip()}")

            except Exception as e:
                logger.warning(f"Log shipping error: {e}")

            await asyncio.sleep(5)  # Check every 5 seconds


class DeploymentAgent:
    """Listens for IoT Jobs and applies CODESYS project updates."""

    def __init__(self, project_path: str, ipc_id: str):
        self.project_path = Path(project_path)
        self.ipc_id = ipc_id

    async def process_job(self, job_document: dict):
        """
        Handle a deployment job from IoT Jobs.
        
        Job document format:
        {
            "operation": "deploy",
            "version": "abc1234",
            "artifact": "s3://bucket/path/ipc-02-cooling.tar.gz"
        }
        """
        operation = job_document.get('operation')
        
        if operation == 'deploy':
            await self._deploy(job_document)
        elif operation == 'rollback':
            await self._rollback()
        elif operation == 'restart':
            await self._restart_codesys()
        else:
            logger.warning(f"Unknown job operation: {operation}")

    async def _deploy(self, job: dict):
        """Download artifact from S3 and deploy to CODESYS."""
        artifact_url = job['artifact']
        version = job['version']
        
        logger.info(f"Deploying version {version} from {artifact_url}")
        
        # 1. Backup current project
        backup_path = self.project_path / f"backup_{int(time.time())}"
        # shutil.copytree(self.project_path, backup_path)
        
        # 2. Download new artifact from S3
        # boto3.client('s3').download_file(...)
        
        # 3. Extract to project directory
        # tarfile.open(...).extractall(self.project_path)
        
        # 4. Restart CODESYS runtime
        # subprocess.run(['systemctl', 'restart', 'codesyscontrol'])
        
        # 5. Verify health (wait for heartbeat)
        await asyncio.sleep(10)
        
        logger.info(f"Deployment complete: version {version}")

    async def _rollback(self):
        """Restore previous project version."""
        logger.info("Rolling back to previous version...")
        # Find most recent backup and restore

    async def _restart_codesys(self):
        """Restart CODESYS runtime without project change."""
        logger.info("Restarting CODESYS runtime...")
        # subprocess.run(['systemctl', 'restart', 'codesyscontrol'])


class HealthReporter:
    """Publishes heartbeat and health status to IoT Core."""

    def __init__(self, site_id: str, ipc_id: str):
        self.site_id = site_id
        self.ipc_id = ipc_id
        self.topic = f"aifactory/{site_id}/{ipc_id}/status"

    def build_health_report(self, resources: dict) -> dict:
        """Build health report payload."""
        return {
            'timestamp': int(time.time() * 1000),
            'site': self.site_id,
            'ipc': self.ipc_id,
            'status': 'healthy' if resources['codesys']['running'] else 'degraded',
            'codesys_running': resources['codesys']['running'],
            'cpu_percent': resources['system']['cpu_percent'],
            'memory_percent': resources['system']['memory_percent'],
            'disk_free_gb': resources['system']['disk_free_gb'],
            'uptime_seconds': int(time.time() - psutil.boot_time()),
        }


async def main():
    """Main agent loop."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s')
    logger.info(f"IPC Agent starting: site={CONFIG['site_id']}, ipc={CONFIG['ipc_id']}")

    monitor = ResourceMonitor(CONFIG['ipc_id'], CONFIG['site_id'])
    log_shipper = LogShipper(CONFIG['codesys_log_path'], CONFIG['site_id'], CONFIG['ipc_id'])
    deployer = DeploymentAgent(CONFIG['codesys_project_path'], CONFIG['ipc_id'])
    health = HealthReporter(CONFIG['site_id'], CONFIG['ipc_id'])

    # Run all services concurrently
    await asyncio.gather(
        log_shipper.tail_and_ship(),
        _metric_loop(monitor, health),
        # In production: IoT Jobs listener loop
    )


async def _metric_loop(monitor: ResourceMonitor, health: HealthReporter):
    """Periodic metric collection and health reporting."""
    while True:
        try:
            resources = monitor.collect()
            report = health.build_health_report(resources)
            
            # In production: publish to IoT Core MQTT
            logger.info(f"Health: {report['status']} | CPU: {report['cpu_percent']:.1f}% | "
                       f"RAM: {report['memory_percent']:.1f}% | CODESYS: {report['codesys_running']}")
            
        except Exception as e:
            logger.error(f"Metric collection error: {e}")

        await asyncio.sleep(CONFIG['metric_interval_s'])


if __name__ == '__main__':
    asyncio.run(main())
