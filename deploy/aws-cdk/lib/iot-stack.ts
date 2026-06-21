import * as cdk from 'aws-cdk-lib';
import * as iot from 'aws-cdk-lib/aws-iot';
import { Construct } from 'constructs';
import { DataStack } from './data-stack';

export interface IoTStackProps extends cdk.StackProps {
  siteId: string;
  environment: string;
  dataStack: DataStack;
}

/**
 * IoT Stack — AWS IoT Core + Device Management
 *
 * Handles:
 *   - Edge gateway MQTT connections (X.509 cert auth)
 *   - Message routing rules (telemetry → Timestream/S3, alarms → Lambda)
 *   - Device provisioning templates
 *   - Least-privilege policies per IPC
 *
 * Cost: ~$1 per million messages
 *   With on-change publishing: ~200K msgs/day = $0.20/day per site
 */
export class IoTStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: IoTStackProps) {
    super(scope, id, props);

    const { siteId, dataStack } = props;
    const siteIdSafe = siteId.replace(/-/g, '_');

    // ─── Thing Group (one per site) ───────────────────────────────────
    new iot.CfnThingGroup(this, 'SiteGroup', {
      thingGroupName: `aifactory-${siteId}`,
      thingGroupProperties: {
        thingGroupDescription: `AI Factory site ${siteId} edge gateways`,
        attributePayload: { attributes: { site: siteId, type: 'edge-gateway' } },
      },
    });

    // ─── Things (one per IPC) ─────────────────────────────────────────
    const ipcNames = ['power', 'cooling', 'environment', 'safety'];
    for (const ipc of ipcNames) {
      new iot.CfnThing(this, `Thing-${ipc}`, {
        thingName: `aifactory-${siteId}-${ipc}`,
        attributePayload: { attributes: { ipc, site: siteId } },
      });
    }

    // ─── IoT Policy (least privilege per site) ────────────────────────
    new iot.CfnPolicy(this, 'EdgePolicy', {
      policyName: `aifactory-${siteId}-edge-policy`,
      policyDocument: {
        Version: '2012-10-17',
        Statement: [
          {
            Effect: 'Allow',
            Action: ['iot:Connect'],
            Resource: [`arn:aws:iot:*:*:client/aifactory-${siteId}-*`],
          },
          {
            Effect: 'Allow',
            Action: ['iot:Publish'],
            Resource: [
              `arn:aws:iot:*:*:topic/aifactory/${siteId}/+/telemetry`,
              `arn:aws:iot:*:*:topic/aifactory/${siteId}/+/alarms`,
              `arn:aws:iot:*:*:topic/aifactory/${siteId}/+/status`,
            ],
          },
          {
            Effect: 'Allow',
            Action: ['iot:Subscribe'],
            Resource: [`arn:aws:iot:*:*:topicfilter/aifactory/${siteId}/+/commands`],
          },
          {
            Effect: 'Allow',
            Action: ['iot:Receive'],
            Resource: [`arn:aws:iot:*:*:topic/aifactory/${siteId}/+/commands`],
          },
        ],
      },
    });

    // ─── Rule: Telemetry → Timestream (hot path) ──────────────────────
    new iot.CfnTopicRule(this, 'RuleTimestream', {
      ruleName: `${siteIdSafe}_telemetry_to_timestream`,
      topicRulePayload: {
        sql: `SELECT * FROM 'aifactory/${siteId}/+/telemetry'`,
        actions: [{
          timestream: {
            databaseName: dataStack.timestreamDbName,
            tableName: dataStack.timestreamTableName,
            roleArn: dataStack.iotRole.roleArn,
            dimensions: [
              { name: 'ipc', value: '${topic(3)}' },
              { name: 'site', value: siteId },
            ],
          },
        }],
        errorAction: {
          cloudwatchLogs: {
            logGroupName: `/aws/iot/aifactory-${siteId}-errors`,
            roleArn: dataStack.iotRole.roleArn,
          },
        },
      },
    });

    // ─── Rule: Telemetry → S3 via Firehose (cold archive) ────────────
    new iot.CfnTopicRule(this, 'RuleS3', {
      ruleName: `${siteIdSafe}_telemetry_to_s3`,
      topicRulePayload: {
        sql: `SELECT * FROM 'aifactory/${siteId}/+/telemetry'`,
        actions: [{
          firehose: {
            deliveryStreamName: dataStack.firehoseName,
            roleArn: dataStack.iotRole.roleArn,
            separator: '\n',
          },
        }],
      },
    });

    // ─── Rule: High-Priority Alarms → Lambda ─────────────────────────
    new iot.CfnTopicRule(this, 'RuleAlarms', {
      ruleName: `${siteIdSafe}_critical_alarms`,
      topicRulePayload: {
        sql: `SELECT * FROM 'aifactory/${siteId}/+/alarms' WHERE severity >= 3`,
        actions: [{
          lambda: {
            functionArn: dataStack.alarmLambda.functionArn,
          },
        }],
      },
    });

    // ─── Outputs ──────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'IoTEndpointCmd', {
      value: 'aws iot describe-endpoint --endpoint-type iot:Data-ATS --query endpointAddress --output text',
      description: 'Run this to get your IoT Core MQTT endpoint',
    });
  }
}
