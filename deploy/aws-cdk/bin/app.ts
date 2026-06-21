#!/usr/bin/env node
/**
 * AWS CDK Application — NVIDIA AI Factory Controls
 * =================================================
 * Cloud infrastructure for multi-site AI factory monitoring.
 *
 * Architecture:
 *   Edge Gateway → AWS IoT Core → IoT Rules →
 *     ├── Timestream (hot/warm time-series)
 *     ├── S3 via Firehose (cold archive, Parquet)
 *     ├── Lambda (alarm processing → SNS)
 *     └── IoT SiteWise (future: asset modeling)
 *
 * Deploy: cdk deploy --all --context siteId=us-west-01
 */

import * as cdk from 'aws-cdk-lib';
import { SecurityStack } from '../lib/security-stack';
import { DataStack } from '../lib/data-stack';
import { IoTStack } from '../lib/iot-stack';
import { MonitoringStack } from '../lib/monitoring-stack';
import { SimulationStack } from '../lib/simulation-stack';
import { FleetDeploymentStack } from '../lib/fleet-deployment-stack';

const app = new cdk.App();

const siteId = app.node.tryGetContext('siteId') ?? 'us-west-01';
const environment = app.node.tryGetContext('environment') ?? 'production';

const env: cdk.Environment = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION ?? 'us-west-2',
};

// Stack deployment order: Security → Data → IoT → Monitoring → Simulation → Fleet
const security = new SecurityStack(app, `AIFactory-${siteId}-Security`, {
  env, siteId, environment,
});

const data = new DataStack(app, `AIFactory-${siteId}-Data`, {
  env, siteId, environment, encryptionKey: security.encryptionKey,
});

const iot = new IoTStack(app, `AIFactory-${siteId}-IoT`, {
  env, siteId, environment, dataStack: data,
});

const monitoring = new MonitoringStack(app, `AIFactory-${siteId}-Monitoring`, {
  env, siteId, environment, dataStack: data,
});

const simulation = new SimulationStack(app, `AIFactory-${siteId}-Simulation`, {
  env, siteId, environment,
});

const fleet = new FleetDeploymentStack(app, `AIFactory-${siteId}-Fleet`, {
  env, siteId, environment,
});

// Explicit dependencies
data.addDependency(security);
iot.addDependency(data);
monitoring.addDependency(data);
simulation.addDependency(security);
fleet.addDependency(iot);

// Tags applied to ALL resources
cdk.Tags.of(app).add('project', 'nvidia-ai-factory-controls');
cdk.Tags.of(app).add('site', siteId);
cdk.Tags.of(app).add('environment', environment);
cdk.Tags.of(app).add('managed-by', 'aws-cdk');
