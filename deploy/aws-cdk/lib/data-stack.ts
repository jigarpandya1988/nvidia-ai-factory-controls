import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as firehose from 'aws-cdk-lib/aws-kinesisfirehose';
import * as timestream from 'aws-cdk-lib/aws-timestream';
import { Construct } from 'constructs';

export interface DataStackProps extends cdk.StackProps {
  siteId: string;
  environment: string;
  encryptionKey: kms.Key;
}

/**
 * Data Stack — Three-Tier Storage Architecture
 *
 * Cost optimization:
 *   HOT:  Timestream memory store — last 24h (real-time dashboards) — $$
 *   WARM: Timestream magnetic store — 90 days (operational queries) — $
 *   COLD: S3 Intelligent-Tiering + Parquet — years (compliance) — ¢
 *
 * Estimated cost (1 site, 500 points, on-change publishing):
 *   Timestream:  ~$50/month
 *   S3:          ~$2/month
 *   Firehose:    ~$5/month
 *   Lambda:      ~$1/month (alarm processing only)
 *   SNS:         ~$0.50/month
 *   TOTAL:       ~$59/month per site
 */
export class DataStack extends cdk.Stack {
  public readonly timestreamDbName: string;
  public readonly timestreamTableName: string;
  public readonly firehoseName: string;
  public readonly archiveBucket: s3.Bucket;
  public readonly alarmLambda: lambda.Function;
  public readonly alarmTopic: sns.Topic;
  public readonly iotRole: iam.Role;

  constructor(scope: Construct, id: string, props: DataStackProps) {
    super(scope, id, props);

    const { siteId, encryptionKey } = props;

    // ─── IAM Role for IoT Rules ───────────────────────────────────────
    this.iotRole = new iam.Role(this, 'IoTRuleRole', {
      assumedBy: new iam.ServicePrincipal('iot.amazonaws.com'),
      description: 'IoT Rules write to Timestream, S3, invoke Lambda',
    });

    // ─── Timestream (Hot + Warm) ──────────────────────────────────────
    this.timestreamDbName = `aifactory-${siteId}`;
    this.timestreamTableName = 'telemetry';

    const tsDb = new timestream.CfnDatabase(this, 'TimestreamDB', {
      databaseName: this.timestreamDbName,
      kmsKeyId: encryptionKey.keyId,
    });

    const tsTable = new timestream.CfnTable(this, 'TimestreamTable', {
      databaseName: this.timestreamDbName,
      tableName: this.timestreamTableName,
      retentionProperties: {
        memoryStoreRetentionPeriodInHours: '24',    // HOT: 24h
        magneticStoreRetentionPeriodInDays: '90',   // WARM: 90 days
      },
      magneticStoreWriteProperties: {
        enableMagneticStoreWrites: true,
      },
    });
    tsTable.addDependency(tsDb);

    this.iotRole.addToPolicy(new iam.PolicyStatement({
      actions: ['timestream:WriteRecords', 'timestream:DescribeEndpoints'],
      resources: ['*'],
    }));

    // ─── S3 Archive (Cold — Intelligent Tiering) ──────────────────────
    this.archiveBucket = new s3.Bucket(this, 'ArchiveBucket', {
      bucketName: `aifactory-${siteId}-archive-${this.account}`,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      intelligentTieringConfigurations: [{
        name: 'auto-tier',
        archiveAccessTierTime: cdk.Duration.days(90),
        deepArchiveAccessTierTime: cdk.Duration.days(365),
      }],
      lifecycleRules: [{
        id: 'retention-7-years',
        expiration: cdk.Duration.days(2555),
      }],
    });

    // ─── Kinesis Firehose (buffer → Parquet → S3) ─────────────────────
    this.firehoseName = `aifactory-${siteId}-telemetry`;

    const firehoseRole = new iam.Role(this, 'FirehoseRole', {
      assumedBy: new iam.ServicePrincipal('firehose.amazonaws.com'),
    });
    this.archiveBucket.grantWrite(firehoseRole);

    const stream = new firehose.CfnDeliveryStream(this, 'Firehose', {
      deliveryStreamName: this.firehoseName,
      deliveryStreamType: 'DirectPut',
      extendedS3DestinationConfiguration: {
        bucketArn: this.archiveBucket.bucketArn,
        roleArn: firehoseRole.roleArn,
        prefix: `telemetry/site=${siteId}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/`,
        errorOutputPrefix: `errors/site=${siteId}/`,
        bufferingHints: {
          intervalInSeconds: 300,  // 5 min buffer (fewer S3 PUTs = cheaper)
          sizeInMBs: 64,
        },
        compressionFormat: 'GZIP',
      },
    });

    this.iotRole.addToPolicy(new iam.PolicyStatement({
      actions: ['firehose:PutRecord', 'firehose:PutRecordBatch'],
      resources: [stream.attrArn],
    }));

    // ─── SNS Alarm Topic ──────────────────────────────────────────────
    this.alarmTopic = new sns.Topic(this, 'AlarmTopic', {
      topicName: `aifactory-${siteId}-alarms`,
      displayName: `AI Factory ${siteId} Critical Alarms`,
      masterKey: encryptionKey,
    });

    // ─── Lambda — Alarm Processor (pay-per-invocation) ────────────────
    this.alarmLambda = new lambda.Function(this, 'AlarmProcessor', {
      functionName: `aifactory-${siteId}-alarm-processor`,
      runtime: lambda.Runtime.NODEJS_20_X,
      handler: 'index.handler',
      code: lambda.Code.fromInline('exports.handler = async (event) => { console.log(event); };'),
      timeout: cdk.Duration.seconds(10),
      memorySize: 128,
      environment: {
        SNS_TOPIC_ARN: this.alarmTopic.topicArn,
        SITE_ID: siteId,
      },
    });
    this.alarmTopic.grantPublish(this.alarmLambda);
    this.alarmLambda.grantInvoke(new iam.ServicePrincipal('iot.amazonaws.com'));

    // ─── Outputs ──────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'TimestreamDBOutput', { value: this.timestreamDbName });
    new cdk.CfnOutput(this, 'ArchiveBucketOutput', { value: this.archiveBucket.bucketName });
    new cdk.CfnOutput(this, 'AlarmTopicOutput', { value: this.alarmTopic.topicArn });
  }
}
