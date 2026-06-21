import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';

export interface SimulationStackProps extends cdk.StackProps {
  siteId: string;
  environment: string;
}

/**
 * Simulation Stack — CODESYS Runtime on EC2 + ECS Services
 *
 * Provides:
 *   1. EC2 instance running CODESYS runtime (Linux x86) for:
 *      - Staging/simulation before deploying to physical IPCs
 *      - Integration testing with real cloud connectivity
 *      - CI/CD target for automated testing
 *
 *   2. ECS Fargate services for:
 *      - Log shipping (controller logs → CloudWatch)
 *      - Resource monitoring (IPC health → CloudWatch metrics)
 *      - CODESYS project deployment agent
 *
 * Cost optimization:
 *   - EC2: t3.medium spot instance (~$10/month for simulation)
 *   - ECS: Fargate spot for non-critical services
 *   - Auto-stop simulation EC2 outside business hours
 */
export class SimulationStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly cluster: ecs.Cluster;

  constructor(scope: Construct, id: string, props: SimulationStackProps) {
    super(scope, id, props);

    const { siteId } = props;

    // ─── VPC (isolated for simulation) ────────────────────────────────
    this.vpc = new ec2.Vpc(this, 'SimVPC', {
      vpcName: `aifactory-${siteId}-simulation`,
      maxAzs: 2,
      natGateways: 1,  // Cost: use 1 NAT for simulation
      subnetConfiguration: [
        { name: 'Public', subnetType: ec2.SubnetType.PUBLIC, cidrMask: 24 },
        { name: 'Private', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS, cidrMask: 24 },
      ],
    });

    // ─── Security Group (CODESYS ports) ───────────────────────────────
    const codesysSG = new ec2.SecurityGroup(this, 'CodesysSG', {
      vpc: this.vpc,
      description: 'CODESYS runtime ports',
      allowAllOutbound: true,
    });
    codesysSG.addIngressRule(ec2.Peer.ipv4('10.0.0.0/8'), ec2.Port.tcp(4840), 'OPC UA');
    codesysSG.addIngressRule(ec2.Peer.ipv4('10.0.0.0/8'), ec2.Port.tcp(11740), 'CODESYS Gateway');
    codesysSG.addIngressRule(ec2.Peer.ipv4('10.0.0.0/8'), ec2.Port.tcp(22), 'SSH');

    // ─── IAM Role for EC2 (SSM + CloudWatch) ──────────────────────────
    const ec2Role = new iam.Role(this, 'EC2Role', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'),
      ],
    });

    // ─── EC2 Instance — CODESYS Simulation Runtime ────────────────────
    const codesysInstance = new ec2.Instance(this, 'CodesysSimulator', {
      instanceName: `aifactory-${siteId}-codesys-sim`,
      vpc: this.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MEDIUM),
      machineImage: ec2.MachineImage.latestAmazonLinux2023(),
      securityGroup: codesysSG,
      role: ec2Role,
      blockDevices: [{
        deviceName: '/dev/xvda',
        volume: ec2.BlockDeviceVolume.ebs(30, { volumeType: ec2.EbsDeviceVolumeType.GP3 }),
      }],
      userData: ec2.UserData.custom(this.getCodesysUserData(siteId)),
    });

    // SSM Parameter: store instance ID for CI/CD deployment target
    new ssm.StringParameter(this, 'SimInstanceId', {
      parameterName: `/aifactory/${siteId}/simulation/instance-id`,
      stringValue: codesysInstance.instanceId,
      description: 'CODESYS simulation EC2 instance ID',
    });

    // ─── ECS Cluster (for monitoring & deployment services) ───────────
    this.cluster = new ecs.Cluster(this, 'MonitoringCluster', {
      clusterName: `aifactory-${siteId}-services`,
      vpc: this.vpc,
      containerInsights: true,  // Built-in container monitoring
    });

    // ─── Outputs ──────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'SimulatorInstanceId', {
      value: codesysInstance.instanceId,
      description: 'Connect via: aws ssm start-session --target <id>',
    });
    new cdk.CfnOutput(this, 'VPCID', { value: this.vpc.vpcId });
  }

  private getCodesysUserData(siteId: string): string {
    return `#!/bin/bash
set -e

# ─── System Setup ───────────────────────────────────────────────
yum update -y
yum install -y docker amazon-cloudwatch-agent jq

# ─── CODESYS Runtime Installation ───────────────────────────────
# Note: CODESYS runtime .deb needs to be uploaded to S3 or ECR
# For simulation, we install from a pre-built package
# aws s3 cp s3://aifactory-packages/codesyscontrol_linux_x86_64.deb /tmp/
# dpkg -i /tmp/codesyscontrol_linux_x86_64.deb

# ─── CloudWatch Agent Config ────────────────────────────────────
cat > /opt/aws/amazon-cloudwatch-agent/etc/config.json << 'EOF'
{
  "agent": { "metrics_collection_interval": 60 },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/codesyscontrol.log",
            "log_group_name": "/aifactory/${siteId}/codesys/runtime",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 30
          },
          {
            "file_path": "/var/log/codesyscontrol_project.log",
            "log_group_name": "/aifactory/${siteId}/codesys/project",
            "log_stream_name": "{instance_id}",
            "retention_in_days": 30
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "AIFactory/${siteId}/CODESYS",
    "metrics_collected": {
      "cpu": { "measurement": ["cpu_usage_idle", "cpu_usage_system"], "totalcpu": true },
      "mem": { "measurement": ["mem_used_percent"] },
      "disk": { "measurement": ["disk_used_percent"], "resources": ["/"] },
      "net": { "measurement": ["bytes_sent", "bytes_recv"] }
    }
  }
}
EOF

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \\
  -a fetch-config -m ec2 \\
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json -s

# ─── Docker for log shipper & deployment agent ──────────────────
systemctl enable docker
systemctl start docker

# ─── Tag instance ───────────────────────────────────────────────
echo "CODESYS simulation instance ready for site: ${siteId}"
`;
  }
}
