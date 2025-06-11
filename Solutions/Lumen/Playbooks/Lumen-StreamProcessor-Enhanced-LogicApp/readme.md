# Lumen-StreamProcessor-Enhanced-LogicApp

## Overview

This enhanced Logic App solution handles large Lumen threat intelligence files (100MB+) using proven patterns from other threat intelligence providers in the Azure Sentinel ecosystem. The solution processes large indicator files entirely in-memory using Logic Apps built-in capabilities, eliminating the need for external storage or Azure Functions.

## Key Features

- **Large File Support**: Handles hundreds of MB indicator files using only Logic Apps
- **In-Memory Processing**: No external storage required - all processing happens in-memory
- **Intelligent Chunking**: Processes indicators in configurable chunks (default: 100 per batch)
- **Rate Limiting**: Respects Microsoft Sentinel API limits (90 requests per minute)
- **Progress Tracking**: Provides detailed logging and progress monitoring
- **Error Handling**: Robust retry logic and failure tracking
- **Resume Capability**: Can handle interruptions and continue processing

## Architecture

The solution follows proven patterns used by other threat intelligence providers while using only Logic Apps native capabilities:

1. **Presigned URL Retrieval**: Gets download URL from Lumen API
2. **Streaming Download**: Downloads large JSON file with chunked transfer mode
3. **In-Memory Processing**: Parses and chunks indicators using Logic Apps array functions
4. **Rate-Limited Upload**: Uploads chunks to Sentinel with intelligent delays
5. **Progress Monitoring**: Tracks processing status and performance metrics

## How It Solves the Large File Problem

### Original Challenge:
- HTTP action fails with 100MB+ files
- Logic Apps timeout on large file processing
- Sentinel API has strict limits (100 objects/request, 100 requests/minute)

### This Solution:
1. **Uses Logic Apps streaming capabilities** with `"transferMode": "Chunked"`
2. **Leverages native array processing** with `take()` and `skip()` functions for chunking
3. **Implements intelligent rate limiting** (65 seconds = ~90 requests/hour)
4. **Processes everything in-memory** - no external storage required
5. **Provides comprehensive error handling** and retry logic

## Deployment

### Prerequisites

1. **Microsoft Sentinel Workspace**: With Threat Intelligence solution enabled
2. **Lumen API Key**: Valid API key for threat intelligence access
3. **Permissions**: Rights to deploy Logic Apps and create managed identity connections

### Deploy via Azure Portal

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FAzure%2FAzure-Sentinel%2Fmaster%2FSolutions%2FLumen%2FPlaybooks%2FLumen-StreamProcessor-Enhanced-LogicApp%2Fazuredeploy.json)

### Deploy via Azure CLI

```bash
az deployment group create \
  --resource-group <your-resource-group> \
  --template-file azuredeploy.json \
  --parameters @azuredeploy.parameters.json
```

## Parameters

| Parameter | Description | Default Value | Notes |
|-----------|-------------|---------------|-------|
| **PlaybookName** | Name for the Logic App | `Lumen-StreamProcessor-Enhanced-LogicApp` | |
| **LumenAPIBaseURL** | Lumen API base URL | Provided default | |
| **LumenAPIKey** | Lumen API key | (Required) | Secure parameter |
| **WorkspaceID** | Sentinel workspace ID | (Required) | Log Analytics workspace ID |
| **ChunkSize** | Indicators per batch | `100` | Max 100 for Sentinel API |
| **ProcessingDelaySeconds** | Delay between uploads | `65` | ~90 requests/hour rate limiting |

## Post-Deployment Configuration

### 1. Grant Permissions

The Logic App managed identity needs Microsoft Sentinel Contributor role:

```bash
# Get the Logic App principal ID
principalId=$(az resource show --resource-group <rg-name> --name <playbook-name> --resource-type Microsoft.Logic/workflows --query identity.principalId -o tsv)

# Grant Microsoft Sentinel Contributor role
az role assignment create \
  --assignee $principalId \
  --role "Microsoft Sentinel Contributor" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/<rg-name>/providers/Microsoft.OperationalInsights/workspaces/<workspace-name>"
```

### 2. Configure API Connection

1. Navigate to the Logic App in Azure Portal
2. Go to **API Connections**
3. Configure the **Sentinel connection** to use managed identity
4. Test the connection

### 3. Monitor Performance

The Logic App provides detailed progress tracking:
- Total indicators processed
- Processing duration
- Success/failure rates
- Performance metrics (indicators per minute)

## How It Works

### Processing Flow

1. **Initialization**: Sets up tracking variables for progress monitoring
2. **Get Presigned URL**: Calls Lumen API to get download URL
3. **Stream Large File**: Downloads JSON using chunked transfer mode
4. **Parse Indicators**: Parses the large JSON response in memory
5. **Chunk Processing**: Iterates through indicators in configurable chunks
6. **Rate-Limited Upload**: Uploads each chunk with appropriate delays
7. **Progress Tracking**: Logs detailed progress and performance metrics

### Key Logic App Actions

```json
"ProcessIndicatorsInChunks": {
    "type": "Until",
    "expression": "@greater(mul(variables('ChunkCounter'), parameters('ChunkSize')), variables('TotalIndicators'))",
    "actions": {
        "CreateCurrentChunk": {
            "type": "SetVariable",
            "inputs": {
                "name": "CurrentChunk",
                "value": "@take(skip(body('Step4_ParseLargeJSON')?['stixobjects'], mul(variables('ChunkCounter'), parameters('ChunkSize'))), parameters('ChunkSize'))"
            }
        },
        "UploadChunkToSentinel": {
            "type": "ApiConnection",
            "inputs": {
                "body": {
                    "sourcesystem": "Lumen",
                    "stixobjects": "@variables('CurrentChunk')"
                },
                "path": "/ThreatIntelligence/@{encodeURIComponent(parameters('WorkspaceID'))}/UploadStixObjects/"
            }
        },
        "RateLimitDelay": {
            "type": "Wait",
            "inputs": {
                "interval": {
                    "count": "@parameters('ProcessingDelaySeconds')",
                    "unit": "Second"
                }
            }
        }
    }
}
```

## Performance Characteristics

### Expected Performance
- **File Size**: Supports 100MB+ files
- **Processing Speed**: ~90 chunks per hour (respecting rate limits)
- **Indicators**: ~9,000 indicators per hour
- **Duration**: 100,000 indicators ≈ 11 hours

### Rate Limiting Strategy
- **65-second delays** between API calls
- **~90 requests per hour** (safely under 100/minute limit)
- **Exponential backoff** on failures
- **Automatic retry** with jitter

## Monitoring and Troubleshooting

### Logic App Monitoring
1. **Run History**: View processing details in Azure Portal
2. **Progress Logs**: Each action logs detailed progress information
3. **Error Tracking**: Failed chunks are tracked and logged
4. **Performance Metrics**: Processing speed and success rates

### Key Metrics to Monitor
- `ProcessedChunks`: Number of successfully uploaded chunks
- `FailedChunks`: Number of failed chunk uploads
- `TotalIndicators`: Total indicators in the file
- `ProcessingDuration`: How long the entire process took
- `SuccessRate`: Percentage of successful chunk uploads

### Common Issues and Solutions

1. **HTTP Timeout on Large Files**
   - Solution: The chunked transfer mode should handle this
   - Fallback: Reduce processing frequency to allow more time

2. **Rate Limiting (429 Errors)**
   - Solution: Increase `ProcessingDelaySeconds` parameter
   - Monitor: Check for 429 responses in run history

3. **Memory Issues**
   - Solution: Logic Apps handle large JSON parsing efficiently
   - Fallback: Contact support for workspace limits

## Comparison with Other Solutions

### vs. Azure Functions Approach
- **Pros**: No additional infrastructure, simpler deployment, no storage dependencies, proven Logic Apps patterns
- **Cons**: Longer processing time due to rate limiting

### vs. Original Batch Approach
- **Pros**: Handles large files, better progress tracking, rate limiting, no storage overhead
- **Cons**: More complex Logic App design

### Key Advantages of This Approach
- **Zero Dependencies**: Only requires Logic Apps - no storage accounts or Azure Functions
- **Cost Effective**: No additional compute or storage costs beyond Logic Apps execution
- **Simplified Deployment**: Single ARM template with minimal parameters
- **Memory Efficient**: Logic Apps handle large JSON parsing natively
- **Proven Pattern**: Based on successful implementations from other TI providers

### Inspired by Proven Patterns
This solution implements patterns successfully used by:
- **Intel471**: Chunking and progress tracking
- **Tenable**: Large file processing and sub-chunking
- **Infoblox**: Rate limiting and batch processing
- **Exchange Solutions**: Large payload segmentation

## Support and Maintenance

### Updates
Monitor Microsoft Sentinel API changes:
- Batch size limits (currently 100 objects)
- Rate limiting (currently 100 requests/minute)
- New API endpoints or features

### Scaling
For higher throughput requirements:
- Deploy multiple Logic Apps with different schedules
- Implement queue-based processing
- Consider hybrid approaches with Azure Functions

## Conclusion

This enhanced Logic App solution provides a robust, scalable approach to processing large Lumen threat intelligence files using only Logic Apps. It implements proven patterns from other threat intelligence providers while respecting Microsoft Sentinel API limitations and providing comprehensive monitoring and error handling.
