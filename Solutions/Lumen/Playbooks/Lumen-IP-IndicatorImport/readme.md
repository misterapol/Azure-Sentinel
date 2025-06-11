# Lumen-IP-IndicatorImport

## Overview

This playbook imports IP threat intelligence indicators from Lumen's API using a two-step presigned URL process and sends them to the **Lumen-ThreatIntelligenceImport** batch processor for ingestion into Microsoft Sentinel's ThreatIntelligenceIndicator table.

## Architecture

The playbook follows the Lumen API workflow pattern:

1. **Step 1**: POST request to `/v1/threat-intelligence/download-url` with x-api-key header to get presigned URL
2. **Step 2**: GET request to the presigned URL (with x-api-key header) to fetch JSON indicators
3. **Step 3**: Transform indicators into STIX format and send to batch processor
4. **Step 4**: Batch processor uploads indicators to Sentinel ThreatIntelligenceIndicator table

## Prerequisites

⚠️ **Important**: These components must be deployed in the following order:

1. **Lumen-ThreatIntelligenceImport** playbook must be deployed first
2. Valid Lumen API key with access to threat intelligence endpoints
3. Microsoft Sentinel workspace with Threat Intelligence solution installed
4. Appropriate permissions to deploy Logic Apps and API connections

**Note**: This playbook includes an inline custom connector for Lumen's API, eliminating the need for separate connector deployment.

## Deployment

### Option 1: Deploy via Azure Portal

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FAzure%2FAzure-Sentinel%2Fmaster%2FSolutions%2FLumen%2FPlaybooks%2FLumen-IP-IndicatorImport%2Fazuredeploy.json)

### Option 2: Deploy via Azure CLI

```bash
az deployment group create \
  --resource-group <your-resource-group> \
  --template-file azuredeploy.json \
  --parameters PlaybookName="Lumen-IP-IndicatorImport" \
               PlaybookNameBatching="Lumen-ThreatIntelligenceImport" \
               LumenAPIBaseURL="https://api.lumen.com"
```

## Parameters

| Parameter | Description | Default Value |
|-----------|-------------|---------------|
| **PlaybookName** | Name for this Logic App | `Lumen-IP-IndicatorImport` |
| **PlaybookNameBatching** | Name of the batch processor Logic App | `Lumen-ThreatIntelligenceImport` |
| **LumenAPIBaseURL** | Base URL for Lumen API endpoints | `https://api.lumen.com` |

## Post-Deployment Configuration

1. **Configure API Connection**
   - Navigate to the deployed Logic App in Azure Portal
   - Go to **API Connections** or edit the Logic App
   - Configure the **Lumen-API-Connection** with your Lumen API key
   - Test the connection

2. **Verify Batch Receiver**
   - Ensure the **Lumen-ThreatIntelligenceImport** playbook is deployed and enabled
   - Verify the batch configuration name matches: `LumenImportToSentinel`

3. **Test the Playbook**
   - Run the Logic App manually from the Azure Portal
   - Monitor the run history for successful execution
   - Check for indicators in the ThreatIntelligenceIndicator table

## Workflow Details

### Trigger
- **Type**: Recurrence
- **Frequency**: Every 6 hours (configurable)
- **Evaluates**: Lumen API for new IP threat indicators

### Actions

1. **Step1_RequestPresignedURL**
   - POST to `/v1/threat-intelligence/download-url`
   - Headers: `x-api-key: <your-api-key>`
   - Body: `{"indicator_type": "ip", "limit": 1000}`

2. **Step2_ValidatePresignedURLResponse**
   - Validates the presigned URL is present in response
   - Terminates with error if invalid

3. **Step3_FetchIndicatorsFromPresignedURL**
   - GET request to the presigned URL
   - Headers: `x-api-key: <your-api-key>`

4. **Step4_ParseIndicatorsJSON**
   - Parses the JSON response containing indicators
   - Expected schema includes indicators array and pagination info

5. **Step5_ProcessIndicators**
   - Validates indicators are present
   - Processes each indicator if available

6. **Step6_ForEachIndicator**
   - Iterates through each IP indicator
   - Transforms to STIX 2.1 format

7. **Step7_SendToBatch**
   - Sends formatted indicator to batch processor
   - Uses `LumenImportToSentinel` batch name

### Data Transformation

The playbook transforms Lumen API indicators into STIX 2.1 format:

```json
{
  "confidence": 50,
  "created": "2025-01-27T00:00:00.000Z",
  "description": "Lumen Threat Intelligence - IP Indicator",
  "id": "indicator--<guid>",
  "indicator_types": ["malicious-activity"],
  "labels": ["threat_types_from_lumen"],
  "modified": "2025-01-27T00:00:00.000Z",
  "name": "192.168.1.1",
  "pattern": "[ipv4-addr:value = '192.168.1.1']",
  "pattern_type": "stix",
  "spec_version": "2.1",
  "type": "indicator",
  "valid_from": "2025-01-27T00:00:00.000Z",
  "valid_until": "2025-02-03T00:00:00.000Z"
}
```

## Expected Lumen API Response

### Step 1 Response (Presigned URL):
```json
{
  "download_url": "https://presigned-url.s3.amazonaws.com/...",
  "expires_at": "2025-01-27T01:00:00.000Z"
}
```

### Step 2 Response (Indicators):
```json
{
  "indicators": [
    {
      "indicator": "192.168.1.1",
      "indicator_type": "ip",
      "confidence": 85,
      "threat_types": ["malware", "c2"],
      "first_seen": "2025-01-20T00:00:00.000Z",
      "last_seen": "2025-01-26T00:00:00.000Z",
      "description": "Known malicious IP address"
    }
  ],
  "pagination": {
    "next_cursor": "abc123",
    "total_count": 1500
  }
}
```

## Monitoring and Troubleshooting

### Check Logic App Runs
```kusto
// Monitor Logic App execution
AzureDiagnostics
| where ResourceProvider == "MICROSOFT.LOGIC"
| where ResourceType == "WORKFLOWS"
| where Resource == "Lumen-IP-IndicatorImport"
| order by TimeGenerated desc
```

### Verify Indicator Ingestion
```kusto
// Check for Lumen indicators
ThreatIntelligenceIndicator 
| where Description == "Lumen Threat Intelligence - IP Indicator"
| summarize Count=count() by bin(TimeGenerated, 1h)
| order by TimeGenerated desc
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| **API Connection Failed** | Invalid API key | Verify API key in connection settings |
| **Presigned URL Invalid** | API endpoint error | Check Lumen API base URL and endpoint |
| **No Indicators Found** | Empty API response | Check API limits and data availability |
| **Batch Send Failed** | Batch receiver not available | Verify Lumen-ThreatIntelligenceImport is enabled |

## Security Considerations

- API key is stored securely in the API connection
- All communication uses HTTPS
- Indicators are processed immediately and not stored locally
- Follow Lumen's API rate limiting guidelines

## Customization

### Adjust Frequency
Modify the recurrence trigger in the Logic App designer:
- Default: Every 6 hours
- Recommended: Between 1-24 hours depending on requirements

### Modify Indicator Limit
Change the `limit` parameter in the POST request:
- Default: 1000 indicators per call
- Maximum: Check Lumen API documentation

### Add Additional Indicator Types
Extend the playbook to support domains, URLs, and hashes by:
1. Duplicating the playbook
2. Changing `indicator_type` parameter
3. Updating the STIX pattern format

## Integration with Sentinel

Once deployed and configured, indicators will appear in:
- **Threat Intelligence blade** in Microsoft Sentinel
- **ThreatIntelligenceIndicator** table in Log Analytics
- Available for correlation with security events via analytics rules

## Support

For issues related to:
- **Logic App functionality**: Contact Azure Support
- **Lumen API access**: Contact Lumen Technologies support
- **Sentinel integration**: Reference Microsoft Sentinel documentation
