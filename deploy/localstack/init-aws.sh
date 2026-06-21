#!/bin/bash
# =============================================================================
# LocalStack Initialization — NVIDIA AI Factory Controls
# =============================================================================
# Creates AWS resources in LocalStack that mirror the production CDK stack.
# This script runs automatically when LocalStack is ready (via init hook).
#
# Resources created:
#   - IoT Things (4 IPCs + 1 edge gateway)
#   - IoT Thing Group
#   - Timestream database + tables
#   - S3 bucket (firmware/config storage)
#   - SNS topics (alarm notifications)
#   - IoT Topic Rules (simplified routing)
# =============================================================================

set -e

ENDPOINT="http://localhost:4566"
REGION="us-west-2"
SITE_ID="local-01"

# Common AWS CLI flags for LocalStack
AWS="aws --endpoint-url=${ENDPOINT} --region=${REGION}"

echo "=============================================="
echo "  Initializing LocalStack AWS Resources"
echo "  Site: ${SITE_ID}"
echo "=============================================="

# ─── IoT Core: Thing Group ────────────────────────────────────────────────────
echo ""
echo "▶ Creating IoT Thing Group..."
${AWS} iot create-thing-group \
    --thing-group-name "aifactory-${SITE_ID}" \
    --thing-group-properties '{
        "thingGroupDescription": "AI Factory site '${SITE_ID}' devices",
        "attributePayload": {
            "attributes": {
                "site_id": "'${SITE_ID}'",
                "environment": "local"
            }
        }
    }' 2>/dev/null || echo "  (already exists)"

# ─── IoT Core: Things (IPCs + Edge Gateway) ──────────────────────────────────
echo ""
echo "▶ Creating IoT Things..."

THINGS=("ipc-power" "ipc-cooling" "ipc-environment" "ipc-safety" "edge-gateway")

for THING in "${THINGS[@]}"; do
    THING_NAME="${SITE_ID}-${THING}"
    echo "  Creating thing: ${THING_NAME}"
    ${AWS} iot create-thing \
        --thing-name "${THING_NAME}" \
        --thing-type-name "ai-factory-ipc" \
        --attribute-payload '{
            "attributes": {
                "site_id": "'${SITE_ID}'",
                "role": "'${THING}'",
                "firmware_version": "1.0.0"
            }
        }' 2>/dev/null || echo "    (already exists)"

    # Add to group
    ${AWS} iot add-thing-to-thing-group \
        --thing-group-name "aifactory-${SITE_ID}" \
        --thing-name "${THING_NAME}" 2>/dev/null || true
done

# ─── Timestream: Database + Tables ───────────────────────────────────────────
echo ""
echo "▶ Creating Timestream database and tables..."

${AWS} timestream-write create-database \
    --database-name "aifactory-telemetry" 2>/dev/null || echo "  (database already exists)"

# Telemetry table (high-frequency sensor data)
${AWS} timestream-write create-table \
    --database-name "aifactory-telemetry" \
    --table-name "sensor_data" \
    --retention-properties '{
        "MemoryStoreRetentionPeriodInHours": 24,
        "MagneticStoreRetentionPeriodInDays": 30
    }' 2>/dev/null || echo "  (sensor_data table already exists)"

# Alarms table
${AWS} timestream-write create-table \
    --database-name "aifactory-telemetry" \
    --table-name "alarms" \
    --retention-properties '{
        "MemoryStoreRetentionPeriodInHours": 168,
        "MagneticStoreRetentionPeriodInDays": 365
    }' 2>/dev/null || echo "  (alarms table already exists)"

# Metrics table (aggregated KPIs)
${AWS} timestream-write create-table \
    --database-name "aifactory-telemetry" \
    --table-name "metrics" \
    --retention-properties '{
        "MemoryStoreRetentionPeriodInHours": 72,
        "MagneticStoreRetentionPeriodInDays": 90
    }' 2>/dev/null || echo "  (metrics table already exists)"

# ─── S3: Firmware + Configuration Bucket ─────────────────────────────────────
echo ""
echo "▶ Creating S3 buckets..."

${AWS} s3 mb "s3://aifactory-${SITE_ID}-firmware" 2>/dev/null || echo "  (firmware bucket already exists)"
${AWS} s3 mb "s3://aifactory-${SITE_ID}-configs" 2>/dev/null || echo "  (configs bucket already exists)"
${AWS} s3 mb "s3://aifactory-${SITE_ID}-logs" 2>/dev/null || echo "  (logs bucket already exists)"

# ─── SNS: Alarm Notification Topics ──────────────────────────────────────────
echo ""
echo "▶ Creating SNS topics..."

${AWS} sns create-topic --name "aifactory-${SITE_ID}-alarms-critical" 2>/dev/null || echo "  (critical topic already exists)"
${AWS} sns create-topic --name "aifactory-${SITE_ID}-alarms-warning" 2>/dev/null || echo "  (warning topic already exists)"
${AWS} sns create-topic --name "aifactory-${SITE_ID}-fleet-events" 2>/dev/null || echo "  (fleet-events topic already exists)"

# ─── IoT Rules (simplified — route telemetry to Timestream) ──────────────────
echo ""
echo "▶ Creating IoT Topic Rules..."

# Create IAM role for IoT rules (required even in LocalStack)
${AWS} iam create-role \
    --role-name "iot-timestream-role" \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "iot.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' 2>/dev/null || echo "  (IAM role already exists)"

ROLE_ARN="arn:aws:iam::000000000000:role/iot-timestream-role"

# Telemetry routing rule
${AWS} iot create-topic-rule \
    --rule-name "aifactory_telemetry_to_timestream" \
    --topic-rule-payload '{
        "sql": "SELECT * FROM '\''aifactory/+/+/telemetry/#'\''",
        "actions": [{
            "timestream": {
                "roleArn": "'${ROLE_ARN}'",
                "databaseName": "aifactory-telemetry",
                "tableName": "sensor_data",
                "dimensions": [
                    {"name": "site_id", "value": "${topic(2)}"},
                    {"name": "subsystem", "value": "${topic(3)}"},
                    {"name": "sensor", "value": "${topic(5)}"}
                ]
            }
        }],
        "ruleDisabled": false
    }' 2>/dev/null || echo "  (telemetry rule already exists)"

# Alarm routing rule
${AWS} iot create-topic-rule \
    --rule-name "aifactory_alarms_to_sns" \
    --topic-rule-payload '{
        "sql": "SELECT * FROM '\''aifactory/+/+/alarms/#'\'' WHERE severity = '\''critical'\''",
        "actions": [{
            "sns": {
                "roleArn": "'${ROLE_ARN}'",
                "targetArn": "arn:aws:sns:'${REGION}':000000000000:aifactory-'${SITE_ID}'-alarms-critical",
                "messageFormat": "JSON"
            }
        }],
        "ruleDisabled": false
    }' 2>/dev/null || echo "  (alarm rule already exists)"

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "=============================================="
echo "  LocalStack Initialization Complete!"
echo "=============================================="
echo ""
echo "  IoT Things:       ${#THINGS[@]}"
echo "  Timestream DB:    aifactory-telemetry (3 tables)"
echo "  S3 Buckets:       3"
echo "  SNS Topics:       3"
echo "  IoT Rules:        2"
echo ""
echo "  Endpoint: ${ENDPOINT}"
echo "  Region:   ${REGION}"
echo ""
echo "  Use with CDK:"
echo "    cdklocal deploy --all --context siteId=${SITE_ID}"
echo ""
echo "  Use with AWS CLI:"
echo "    aws --endpoint-url=${ENDPOINT} iot list-things"
echo ""
