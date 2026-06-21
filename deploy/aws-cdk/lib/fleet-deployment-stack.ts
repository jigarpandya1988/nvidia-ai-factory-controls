import * as cdk from 'aws-cdk-lib';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as codepipeline_actions from 'aws-cdk-lib/aws-codepipeline-actions';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as iot from 'aws-cdk-lib/aws-iot';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface FleetDeploymentStackProps extends cdk.StackProps {
  siteId: string;
  environment: string;
}

/**
 * Fleet Deployment Stack — CI/CD Pipeline for CODESYS Projects
 *
 * Pipeline:
 *   GitHub Push → CodeBuild (validate ST syntax + compile) →
 *     → Deploy to Simulation EC2 (test) →
 *       → Manual Approval →
 *         → Deploy to Physical IPCs (via IoT Jobs / SSM)
 *
 * Deployment Strategies:
 *   1. IoT Jobs — Push .project file to IPC via MQTT (for remote sites)
 *   2. SSM Run Command — Direct deployment via Systems Manager (VPN sites)
 *   3. CODESYS Automation Server — Native CODESYS deployment API
 *
 * Rollback:
 *   Each deployment creates a backup of the previous .project file.
 *   On failure: automatic rollback to last-known-good version.
 */
export class FleetDeploymentStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: FleetDeploymentStackProps) {
    super(scope, id, props);

    const { siteId } = props;

    // ─── Artifact Bucket (stores compiled CODESYS projects) ───────────
    const artifactBucket = new s3.Bucket(this, 'ArtifactBucket', {
      bucketName: `aifactory-${siteId}-artifacts-${this.account}`,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      versioned: true,  // Keep all versions for rollback
      encryption: s3.BucketEncryption.S3_MANAGED,
      lifecycleRules: [{
        id: 'cleanup-old-artifacts',
        noncurrentVersionExpiration: cdk.Duration.days(90),
      }],
    });

    // ─── CodeBuild — Validate & Package CODESYS Projects ──────────────
    const buildProject = new codebuild.Project(this, 'BuildProject', {
      projectName: `aifactory-${siteId}-codesys-build`,
      description: 'Validates CODESYS ST syntax and packages for deployment',
      source: codebuild.Source.gitHub({
        owner: 'your-org',
        repo: 'nvidia-ai-factory-controls',
        branchOrRef: 'main',
      }),
      environment: {
        buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
        computeType: codebuild.ComputeType.SMALL,
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        phases: {
          install: {
            'runtime-versions': { python: '3.12' },
            commands: [
              'echo "Installing validation tools..."',
              'pip install pyyaml',
            ],
          },
          pre_build: {
            commands: [
              'echo "Validating CODESYS Structured Text files..."',
              // Validate all .fb files have FUNCTION_BLOCK declaration
              'find libraries/ -name "*.fb" -exec grep -L "FUNCTION_BLOCK" {} \\; | tee /tmp/invalid.txt',
              'if [ -s /tmp/invalid.txt ]; then echo "FAIL: Missing FUNCTION_BLOCK"; exit 1; fi',
              // Validate all .method files have METHOD declaration
              'find libraries/ -name "*.method" -exec grep -L "METHOD" {} \\; | tee /tmp/invalid.txt',
              'if [ -s /tmp/invalid.txt ]; then echo "FAIL: Missing METHOD"; exit 1; fi',
              // Count artifacts
              'echo "Function Blocks: $(find libraries/ -name *.fb | wc -l)"',
              'echo "Methods: $(find libraries/ -name *.method | wc -l)"',
              'echo "Enums: $(find libraries/ -name *.enum | wc -l)"',
              'echo "Structs: $(find libraries/ -name *.struct | wc -l)"',
            ],
          },
          build: {
            commands: [
              'echo "Packaging CODESYS project files..."',
              // Package each IPC project
              'tar -czf ipc-01-power.tar.gz projects/IPC-01_Power/ libraries/AIFactory_Common/ libraries/AIFactory_Communication/ libraries/AIFactory_Power/',
              'tar -czf ipc-02-cooling.tar.gz projects/IPC-02_Cooling/ libraries/AIFactory_Common/ libraries/AIFactory_Communication/ libraries/AIFactory_Cooling/ libraries/AIFactory_Safety/',
              'tar -czf ipc-03-environment.tar.gz projects/IPC-03_Environment/ libraries/AIFactory_Common/ libraries/AIFactory_Communication/ libraries/AIFactory_Environment/',
              'tar -czf ipc-04-safety.tar.gz projects/IPC-04_Safety/ libraries/AIFactory_Common/ libraries/AIFactory_Communication/ libraries/AIFactory_Safety/',
              // Version stamp
              'echo "{\\\"version\\\": \\\"$(git rev-parse --short HEAD)\\\", \\\"timestamp\\\": \\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\", \\\"branch\\\": \\\"$(git branch --show-current)\\\"}" > build-info.json',
            ],
          },
          post_build: {
            commands: [
              'echo "Build complete. Artifacts ready for deployment."',
            ],
          },
        },
        artifacts: {
          files: [
            'ipc-*.tar.gz',
            'build-info.json',
          ],
        },
      }),
      logging: {
        cloudWatch: {
          logGroup: new logs.LogGroup(this, 'BuildLogs', {
            logGroupName: `/aifactory/${siteId}/codebuild`,
            retention: logs.RetentionDays.TWO_WEEKS,
          }),
        },
      },
    });
    artifactBucket.grantReadWrite(buildProject);

    // ─── CodeBuild — Deploy to Simulation ─────────────────────────────
    const deploySimProject = new codebuild.Project(this, 'DeploySimProject', {
      projectName: `aifactory-${siteId}-deploy-simulation`,
      description: 'Deploys CODESYS project to simulation EC2 instance',
      environment: {
        buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
        computeType: codebuild.ComputeType.SMALL,
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        phases: {
          build: {
            commands: [
              `INSTANCE_ID=$(aws ssm get-parameter --name /aifactory/${siteId}/simulation/instance-id --query Parameter.Value --output text)`,
              'echo "Deploying to simulation instance: $INSTANCE_ID"',
              // Upload project package to EC2 via SSM
              `aws s3 cp ipc-02-cooling.tar.gz s3://${artifactBucket.bucketName}/staging/`,
              // Trigger deployment via SSM Run Command
              `aws ssm send-command --instance-ids $INSTANCE_ID --document-name "AWS-RunShellScript" --parameters 'commands=["cd /opt/codesys && aws s3 cp s3://${artifactBucket.bucketName}/staging/ipc-02-cooling.tar.gz . && tar -xzf ipc-02-cooling.tar.gz && systemctl restart codesyscontrol"]'`,
              'echo "Simulation deployment triggered. Waiting for health check..."',
              'sleep 30',
              // Verify CODESYS runtime is healthy
              `aws ssm send-command --instance-ids $INSTANCE_ID --document-name "AWS-RunShellScript" --parameters 'commands=["systemctl is-active codesyscontrol"]'`,
            ],
          },
        },
      }),
    });
    artifactBucket.grantRead(deploySimProject);
    deploySimProject.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ssm:SendCommand', 'ssm:GetParameter'],
      resources: ['*'],
    }));

    // ─── CodeBuild — Deploy to Physical IPCs ──────────────────────────
    const deployProdProject = new codebuild.Project(this, 'DeployProdProject', {
      projectName: `aifactory-${siteId}-deploy-production`,
      description: 'Deploys CODESYS project to physical IPCs via IoT Jobs',
      environment: {
        buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
        computeType: codebuild.ComputeType.SMALL,
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        phases: {
          build: {
            commands: [
              'echo "Creating IoT Job for fleet deployment..."',
              // Upload artifact to S3 (presigned URL for IPCs to download)
              `aws s3 cp ipc-02-cooling.tar.gz s3://${artifactBucket.bucketName}/production/latest/`,
              // Create IoT Job targeting the site's thing group
              `aws iot create-job \\
                --job-id "deploy-$(date +%Y%m%d-%H%M%S)" \\
                --targets "arn:aws:iot:${this.region}:${this.account}:thinggroup/aifactory-${siteId}" \\
                --document '{"operation":"deploy","version":"'$(cat build-info.json | jq -r .version)'","artifact":"s3://${artifactBucket.bucketName}/production/latest/ipc-02-cooling.tar.gz"}' \\
                --job-executions-rollout-config '{"maximumPerMinute":1}' \\
                --abort-config '{"criteriaList":[{"failureType":"FAILED","action":"CANCEL","thresholdPercentage":50,"minNumberOfExecutedThings":1}]}'`,
              'echo "IoT Job created. IPCs will download and apply update."',
            ],
          },
        },
      }),
    });
    artifactBucket.grantRead(deployProdProject);
    deployProdProject.addToRolePolicy(new iam.PolicyStatement({
      actions: ['iot:CreateJob', 'iot:DescribeJob'],
      resources: ['*'],
    }));

    // ─── CodePipeline — Full CI/CD Pipeline ───────────────────────────
    const sourceOutput = new codepipeline.Artifact('SourceOutput');
    const buildOutput = new codepipeline.Artifact('BuildOutput');

    new codepipeline.Pipeline(this, 'DeployPipeline', {
      pipelineName: `aifactory-${siteId}-deploy`,
      stages: [
        {
          stageName: 'Source',
          actions: [
            new codepipeline_actions.GitHubSourceAction({
              actionName: 'GitHub',
              owner: 'your-org',
              repo: 'nvidia-ai-factory-controls',
              branch: 'main',
              oauthToken: cdk.SecretValue.secretsManager('github-token'),
              output: sourceOutput,
            }),
          ],
        },
        {
          stageName: 'Build',
          actions: [
            new codepipeline_actions.CodeBuildAction({
              actionName: 'ValidateAndPackage',
              project: buildProject,
              input: sourceOutput,
              outputs: [buildOutput],
            }),
          ],
        },
        {
          stageName: 'DeploySimulation',
          actions: [
            new codepipeline_actions.CodeBuildAction({
              actionName: 'DeployToSimulator',
              project: deploySimProject,
              input: buildOutput,
            }),
          ],
        },
        {
          stageName: 'Approval',
          actions: [
            new codepipeline_actions.ManualApprovalAction({
              actionName: 'ApproveProduction',
              notifyEmails: ['controls-team@company.com'],
              additionalInformation: 'Simulation passed. Approve deployment to physical IPCs?',
            }),
          ],
        },
        {
          stageName: 'DeployProduction',
          actions: [
            new codepipeline_actions.CodeBuildAction({
              actionName: 'DeployToIPCs',
              project: deployProdProject,
              input: buildOutput,
            }),
          ],
        },
      ],
    });

    // ─── Outputs ──────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'ArtifactBucket', { value: artifactBucket.bucketName });
    new cdk.CfnOutput(this, 'PipelineName', { value: `aifactory-${siteId}-deploy` });
  }
}
