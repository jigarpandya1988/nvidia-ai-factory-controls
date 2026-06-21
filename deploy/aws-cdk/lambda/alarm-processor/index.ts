/**
 * Alarm Processor Lambda — NVIDIA AI Factory Controls
 *
 * Triggered by IoT Rule when severity >= 3 (HIGH/CRITICAL).
 * Formats alarm and publishes to SNS for operator notification.
 *
 * Cost: $0 when no alarms. ~$0.0000002 per invocation when alarms fire.
 */

import { SNSClient, PublishCommand } from '@aws-sdk/client-sns';

const sns = new SNSClient({});
const TOPIC_ARN = process.env.SNS_TOPIC_ARN!;
const SITE_ID = process.env.SITE_ID!;

interface AlarmEvent {
  ipc: string;
  severity: number;
  source: string;
  message: string;
  timestamp: number;
  value?: number;
  threshold?: number;
}

const SEVERITY_LABELS: Record<number, string> = {
  3: '🟠 HIGH',
  4: '🔴 CRITICAL',
};

export async function handler(event: AlarmEvent): Promise<void> {
  const severityLabel = SEVERITY_LABELS[event.severity] ?? `⚪ LEVEL ${event.severity}`;
  const time = new Date(event.timestamp).toISOString();

  const subject = `[${severityLabel}] AI Factory ${SITE_ID} — ${event.source}`;
  const body = [
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`,
    `  ${severityLabel}`,
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`,
    ``,
    `  Site:      ${SITE_ID}`,
    `  IPC:       ${event.ipc}`,
    `  Source:    ${event.source}`,
    `  Message:   ${event.message}`,
    `  Time:      ${time}`,
    event.value !== undefined ? `  Value:     ${event.value}` : '',
    event.threshold !== undefined ? `  Threshold: ${event.threshold}` : '',
    ``,
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`,
    `  Action Required: Investigate immediately.`,
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`,
  ].filter(Boolean).join('\n');

  await sns.send(new PublishCommand({
    TopicArn: TOPIC_ARN,
    Subject: subject.substring(0, 100), // SNS subject limit
    Message: body,
    MessageAttributes: {
      severity: { DataType: 'Number', StringValue: String(event.severity) },
      site: { DataType: 'String', StringValue: SITE_ID },
      ipc: { DataType: 'String', StringValue: event.ipc },
    },
  }));

  console.log(`Published alarm: ${subject}`);
}
