import * as cdk from 'aws-cdk-lib';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as sm from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export interface SecurityStackProps extends cdk.StackProps {
  siteId: string;
  environment: string;
}

/**
 * Security Stack — Encryption, Secrets, and Access Control
 *
 * Zero-trust model:
 *   - KMS key for all data at rest (auto-rotation enabled)
 *   - Secrets Manager for credentials (no hardcoded passwords)
 *   - Least-privilege IAM roles
 *   - X.509 device certificates for IoT (provisioned separately)
 */
export class SecurityStack extends cdk.Stack {
  public readonly encryptionKey: kms.Key;
  public readonly edgeRole: iam.Role;

  constructor(scope: Construct, id: string, props: SecurityStackProps) {
    super(scope, id, props);

    // ─── KMS Key (encrypts Timestream, S3, Secrets) ───────────────────
    this.encryptionKey = new kms.Key(this, 'DataKey', {
      alias: `alias/aifactory-${props.siteId}`,
      description: `AI Factory ${props.siteId} data encryption`,
      enableKeyRotation: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ─── Secrets Manager (edge gateway credentials) ───────────────────
    new sm.Secret(this, 'EdgeSecret', {
      secretName: `aifactory/${props.siteId}/edge-gateway`,
      description: 'Edge gateway connection credentials',
      generateSecretString: {
        secretStringTemplate: JSON.stringify({ username: 'edge-gateway' }),
        generateStringKey: 'password',
        excludePunctuation: true,
        passwordLength: 32,
      },
      encryptionKey: this.encryptionKey,
    });

    // ─── IAM Role for Edge Gateways ───────────────────────────────────
    this.edgeRole = new iam.Role(this, 'EdgeRole', {
      assumedBy: new iam.ServicePrincipal('credentials.iot.amazonaws.com'),
      description: 'Assumed by edge gateways via IoT credential provider',
      maxSessionDuration: cdk.Duration.hours(12),
    });

    // ─── Outputs ──────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'KMSKeyArn', { value: this.encryptionKey.keyArn });
    new cdk.CfnOutput(this, 'EdgeRoleArn', { value: this.edgeRole.roleArn });
  }
}
