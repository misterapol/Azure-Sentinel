# Simplified Lumen Threat Intelligence Integration

## Overview

This simplified approach addresses the challenges with processing large threat intelligence files in Logic Apps by using proven patterns from other TI providers like Recorded Future and Intel471.

## Architecture

### Two-Playbook Design

1. **Lumen-IndicatorCollector-Simple**: Handles data collection and chunking
2. **Lumen-ThreatIntelligenceImport-Simple**: Handles batch upload to Sentinel

### Key Improvements

1. **Smaller Chunks**: Processes 1MB chunks instead of trying to load entire 170MB file
2. **Proven Upload Pattern**: Uses the same upload mechanism as Recorded Future
3. **Batch Processing**: Collects indicators in batches of 100 before uploading
4. **Better Error Handling**: Includes retry policies and timeout limits
5. **Separation of Concerns**: Collection logic separate from upload logic

## Deployment Steps

### 1. Deploy the Batch Processor First
```bash
az deployment group create \
  --resource-group your-rg \
  --template-file Lumen-ThreatIntelligenceImport-Simple/azuredeploy.json \
  --parameters PlaybookName="Lumen-ThreatIntelligenceImport" WorkspaceID="your-workspace-id"
```

### 2. Deploy the Collector
```bash
az deployment group create \
  --resource-group your-rg \
  --template-file Lumen-IndicatorCollector-Simple/azuredeploy.json \
  --parameters PlaybookName="Lumen-IndicatorCollector-Simple" LumenAPIKey="your-api-key"
```

### 3. Configure Connections
1. Go to the deployed Logic Apps in Azure Portal
2. Edit the Lumen-ThreatIntelligenceImport playbook
3. Authorize the Azure Sentinel connection using managed identity
4. Save the playbook

## How It Works

### Collection Flow
1. **Get Presigned URL**: Calls Lumen API to get download URL
2. **Process in Chunks**: Downloads 1MB chunks using HTTP Range headers
3. **Parse JSON Lines**: Splits each chunk into individual JSON indicators
4. **Send to Batch**: Sends each indicator to the batch processor

### Upload Flow
1. **Batch Trigger**: Collects up to 100 indicators or waits 5 minutes
2. **Transform**: Selects indicator content from batch
3. **Upload**: Uses Azure Sentinel connector to upload to ThreatIntelligenceIndicator table

## Key Differences from Complex Version

### What We Removed
- Complex buffer management
- STIX bundle creation
- Manual retry logic for 429 errors
- Variable chunking strategies
- Multiple status tracking variables

### What We Kept
- Presigned URL pattern (Lumen API requirement)
- Range-based downloading
- Error handling and timeouts
- Batch processing for efficiency

## Advantages

1. **Simplicity**: Much easier to debug and maintain
2. **Reliability**: Uses proven patterns from successful TI providers
3. **Scalability**: Can handle large files without memory issues
4. **Maintainability**: Clear separation of concerns
5. **Observability**: Easier to monitor and troubleshoot

## Testing Strategy

### Start Small
1. Test with a smaller file first (if available)
2. Verify upload mechanism works with batch processor
3. Gradually increase chunk sizes if needed

### Monitor
- Check Logic App run history for errors
- Monitor ThreatIntelligenceIndicator table for data arrival
- Watch for any timeout or memory issues

## Fallback Options

If Logic Apps still struggle with large files:

1. **Azure Functions**: Use the CrowdStrike pattern with Azure Functions
2. **Alternative APIs**: Check if Lumen offers paginated APIs
3. **External Processing**: Use external service to break down file, then import

## Comparison with Other Providers

| Provider | Method | File Size | Complexity |
|----------|--------|-----------|------------|
| **Recorded Future** | Batch API | Small batches | Low |
| **Intel471** | STIX Upload | Medium files | Medium |
| **Group-IB** | Graph API | Small batches | Low |
| **CrowdStrike** | Azure Functions | Any size | High |
| **Lumen (New)** | Batch API | Large chunks | Low-Medium |

This approach follows the **Recorded Future** pattern, which is proven to work reliably at scale.

## Next Steps

1. Deploy and test the simplified version
2. Monitor performance and reliability
3. If successful, consider adding features like:
   - Better error reporting
   - Metrics collection
   - Custom retry policies
   - Data validation
