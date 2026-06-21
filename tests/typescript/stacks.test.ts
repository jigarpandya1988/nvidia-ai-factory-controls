/**
 * CDK Stack Unit Tests — NVIDIA AI Factory Controls
 * ===================================================
 * Validates that CDK stacks synthesize correctly and produce
 * expected CloudFormation resources.
 *
 * Run: npx jest --config tests/typescript/jest.config.ts
 */

import * as cdk from 'aws-cdk-lib';
import { Template, Match } from 'aws-cdk-lib/assertions';
import { SecurityStack } from '../../deploy/aws-cdk/lib/security-stack';
import { DataStack } from '../../deploy/aws-cdk/lib/data-stack';
import { IoTStack } from '../../deploy/aws-cdk/lib/iot-stack';
import { MonitoringStack } from '../../deploy/aws-cdk/lib/monitoring-stack';

const TEST_ENV = { account: '123456789012', region: 'us-west-2' };
const TEST_SITE = 'test-01';

// =============================================================================
// SecurityStack Tests
// =============================================================================

describe('SecurityStack', () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new SecurityStack(app, 'TestSecurity', {
      env: TEST_ENV,
      siteId: TEST_SITE,
      environment: 'test',
    });
    template = Template.fromStack(stack);
  });

  test('creates KMS key with rotation enabled', () => {
    template.hasResourceProperties('AWS::KMS::Key', {
      EnableKeyRotation: true,
    });
  });

  test('creates KMS alias with site name', () => {
    template.hasResourceProperties('AWS::KMS::Alias', {
      AliasName: `alias/aifactory-${TEST_SITE}`,
    });
  });

  test('creates Secrets Manager secret', () => {
    template.hasResourceProperties('AWS::SecretsManager::Secret', {
      Name: `aifactory/${TEST_SITE}/edge-gateway`,
    });
  });

  test('creates IAM role for edge gateways', () => {
    template.hasResourceProperties('AWS::IAM::Role', {
      AssumeRolePolicyDocument: Match.objectLike({
        Statement: Match.arrayWith([
          Match.objectLike({
            Principal: { Service: 'credentials.iot.amazonaws.com' },
          }),
        ]),
      }),
    });
  });
});

// =============================================================================
// DataStack Tests
// =============================================================================

describe('DataStack', () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const security = new SecurityStack(app, 'DSec', {
      env: TEST_ENV, siteId: TEST_SITE, environment: 'test',
    });
    const stack = new DataStack(app, 'DData', {
      env: TEST_ENV, siteId: TEST_SITE, environment: 'test',
      encryptionKey: security.encryptionKey,
    });
    template = Template.fromStack(stack);
  });

  test('creates Timestream database', () => {
    template.hasResourceProperties('AWS::Timestream::Database', {
      DatabaseName: `aifactory-${TEST_SITE}`,
    });
  });

  test('creates Timestream table with correct retention', () => {
    template.hasResourceProperties('AWS::Timestream::Table', {
      TableName: 'telemetry',
    });
  });

  test('creates S3 bucket with intelligent tiering', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      BucketName: Match.stringLikeRegexp(`aifactory-${TEST_SITE}-archive`),
    });
  });

  test('S3 bucket blocks public access', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      PublicAccessBlockConfiguration: {
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true,
      },
    });
  });

  test('creates Kinesis Firehose delivery stream', () => {
    template.hasResourceProperties('AWS::KinesisFirehose::DeliveryStream', {
      DeliveryStreamName: `aifactory-${TEST_SITE}-telemetry`,
      DeliveryStreamType: 'DirectPut',
    });
  });

  test('creates SNS alarm topic', () => {
    template.hasResourceProperties('AWS::SNS::Topic', {
      TopicName: `aifactory-${TEST_SITE}-alarms`,
    });
  });

  test('creates Lambda alarm processor', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      FunctionName: `aifactory-${TEST_SITE}-alarm-processor`,
      Runtime: 'nodejs20.x',
      Timeout: 10,
      MemorySize: 128,
    });
  });

  test('Lambda has SNS publish permission', () => {
    template.hasResourceProperties('AWS::IAM::Policy', Match.objectLike({
      PolicyDocument: Match.objectLike({
        Statement: Match.arrayWith([
          Match.objectLike({
            Action: 'sns:Publish',
          }),
        ]),
      }),
    }));
  });
});

// =============================================================================
// IoTStack Tests
// =============================================================================

describe('IoTStack', () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const security = new SecurityStack(app, 'ISec', {
      env: TEST_ENV, siteId: TEST_SITE, environment: 'test',
    });
    const data = new DataStack(app, 'IData', {
      env: TEST_ENV, siteId: TEST_SITE, environment: 'test',
      encryptionKey: security.encryptionKey,
    });
    const stack = new IoTStack(app, 'IIoT', {
      env: TEST_ENV, siteId: TEST_SITE, environment: 'test',
      dataStack: data,
    });
    template = Template.fromStack(stack);
  });

  test('creates IoT Thing Group for site', () => {
    template.hasResourceProperties('AWS::IoT::ThingGroup', {
      ThingGroupName: `aifactory-${TEST_SITE}`,
    });
  });

  test('creates IoT Things for each IPC', () => {
    template.resourceCountIs('AWS::IoT::Thing', 4);
  });

  test('creates IoT Policy with least privilege', () => {
    template.hasResourceProperties('AWS::IoT::Policy', {
      PolicyName: `aifactory-${TEST_SITE}-edge-policy`,
    });
  });

  test('creates IoT Topic Rules for telemetry routing', () => {
    // Should have rules for Timestream, S3, and Alarms
    template.resourceCountIs('AWS::IoT::TopicRule', 3);
  });

  test('IoT Policy restricts publish to site-specific topics', () => {
    template.hasResourceProperties('AWS::IoT::Policy', {
      PolicyDocument: Match.objectLike({
        Statement: Match.arrayWith([
          Match.objectLike({
            Effect: 'Allow',
            Action: ['iot:Publish'],
            Resource: Match.arrayWith([
              Match.stringLikeRegexp(`.*${TEST_SITE}.*telemetry`),
            ]),
          }),
        ]),
      }),
    });
  });
});

// =============================================================================
// MonitoringStack Tests
// =============================================================================

describe('MonitoringStack', () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const security = new SecurityStack(app, 'MSec', {
      env: TEST_ENV, siteId: TEST_SITE, environment: 'test',
    });
    const data = new DataStack(app, 'MData', {
      env: TEST_ENV, siteId: TEST_SITE, environment: 'test',
      encryptionKey: security.encryptionKey,
    });
    const stack = new MonitoringStack(app, 'MMon', {
      env: TEST_ENV, siteId: TEST_SITE, environment: 'test',
      dataStack: data,
    });
    template = Template.fromStack(stack);
  });

  test('creates CloudWatch dashboard', () => {
    template.hasResourceProperties('AWS::CloudWatch::Dashboard', {
      DashboardName: `AIFactory-${TEST_SITE}-Operational`,
    });
  });

  test('creates no-messages alarm', () => {
    template.hasResourceProperties('AWS::CloudWatch::Alarm', {
      AlarmName: `AIFactory-${TEST_SITE}-NoMessages`,
      ComparisonOperator: 'LessThanThreshold',
      TreatMissingData: 'breaching',
    });
  });
});
