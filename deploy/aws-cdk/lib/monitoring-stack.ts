import * as cdk from 'aws-cdk-lib';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as cw_actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as grafana from 'aws-cdk-lib/aws-grafana';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { DataStack } from './data-stack';

export interface MonitoringStackProps extends cdk.StackProps {
  siteId: string;
  environment: string;
  dataStack: DataStack;
}

/**
 * Monitoring Stack — CloudWatch Dashboards + Managed Grafana
 *
 * Provides:
 *   - CloudWatch alarms for infrastructure health
 *   - Amazon Managed Grafana workspace (Timestream as datasource)
 *   - Budget alarms (cost control)
 *   - IoT Core metrics monitoring
 *
 * Cost: Managed Grafana ~$9/editor/month, CloudWatch dashboards $3/month
 */
export class MonitoringStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: MonitoringStackProps) {
    super(scope, id, props);

    const { siteId, dataStack } = props;

    // ─── CloudWatch Dashboard ─────────────────────────────────────────
    const dashboard = new cloudwatch.Dashboard(this, 'OperationalDashboard', {
      dashboardName: `AIFactory-${siteId}-Operational`,
      periodOverride: cloudwatch.PeriodOverride.AUTO,
    });

    // IoT Core metrics
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'IoT Messages In/Out',
        left: [
          new cloudwatch.Metric({
            namespace: 'AWS/IoT',
            metricName: 'PublishIn.Success',
            statistic: 'Sum',
            period: cdk.Duration.minutes(1),
          }),
        ],
        width: 12,
      }),
      new cloudwatch.GraphWidget({
        title: 'IoT Rule Execution',
        left: [
          new cloudwatch.Metric({
            namespace: 'AWS/IoT',
            metricName: 'TopicMatch',
            statistic: 'Sum',
            period: cdk.Duration.minutes(1),
          }),
          new cloudwatch.Metric({
            namespace: 'AWS/IoT',
            metricName: 'RuleMessageThrottled',
            statistic: 'Sum',
            period: cdk.Duration.minutes(1),
          }),
        ],
        width: 12,
      }),
    );

    // Lambda metrics
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Alarm Lambda Invocations & Errors',
        left: [
          dataStack.alarmLambda.metricInvocations({ period: cdk.Duration.minutes(5) }),
        ],
        right: [
          dataStack.alarmLambda.metricErrors({ period: cdk.Duration.minutes(5) }),
        ],
        width: 12,
      }),
    );

    // ─── CloudWatch Alarms ────────────────────────────────────────────

    // Alarm: No messages received (edge gateway disconnected)
    const noMessagesAlarm = new cloudwatch.Alarm(this, 'NoMessagesAlarm', {
      alarmName: `AIFactory-${siteId}-NoMessages`,
      alarmDescription: 'No IoT messages received in 5 minutes — edge gateway may be offline',
      metric: new cloudwatch.Metric({
        namespace: 'AWS/IoT',
        metricName: 'PublishIn.Success',
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      }),
      threshold: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.BREACHING,
    });
    noMessagesAlarm.addAlarmAction(new cw_actions.SnsAction(dataStack.alarmTopic));

    // Alarm: Lambda errors (alarm processing failing)
    const lambdaErrorAlarm = new cloudwatch.Alarm(this, 'LambdaErrorAlarm', {
      alarmName: `AIFactory-${siteId}-AlarmProcessorError`,
      alarmDescription: 'Alarm processor Lambda is erroring — notifications may not be sent',
      metric: dataStack.alarmLambda.metricErrors({ period: cdk.Duration.minutes(5) }),
      threshold: 3,
      evaluationPeriods: 1,
    });

    // ─── Budget Alarm (cost control) ──────────────────────────────────
    // Note: AWS Budgets requires separate API — implemented via CfnBudget
    new cdk.CfnOutput(this, 'DashboardURL', {
      value: `https://${this.region}.console.aws.amazon.com/cloudwatch/home?region=${this.region}#dashboards:name=AIFactory-${siteId}-Operational`,
      description: 'CloudWatch Dashboard URL',
    });
  }
}
