# Lumen Threat Intelligence Connector for Microsoft Sentinel

This Azure Function connects to the Lumen Threat Intelligence API and uploads threat indicators to Microsoft Sentinel using the new STIX Objects API.

## Overview

The Lumen Threat Intelligence Connector:
1. **Requests presigned URL** from Lumen API via POST request
2. **Downloads threat data** from the presigned URL via GET request  
3. **Extracts STIX objects** from the `stixobjects` array in the response
4. **Uploads indicators** to Microsoft Sentinel using the new STIX Objects API
5. **Respects rate limits** (100 objects per request, 100 requests per minute)

## Features

- ✅ **New STIX Objects API** - Uses the latest 2024-02-01-preview API
- ✅ **Two-step Lumen process** - POST for presigned URL, GET for data
- ✅ **Rate limiting** - Built-in respect for API limits  
- ✅ **Batch processing** - Handles large datasets efficiently
- ✅ **Error handling** - Comprehensive retry logic and error reporting
- ✅ **Managed Identity** - Secure authentication without secrets

## Prerequisites

1. **Microsoft Sentinel workspace** with Threat Intelligence enabled
2. **Lumen API access** with valid API key and base URL
3. **Azure App Registration** with Microsoft Sentinel Contributor role
4. **Azure Function App** (Python 3.9+ runtime)

## Environment Variables

Configure these environment variables in your Azure Function App:

| Variable | Description | Example |
|----------|-------------|---------|
| `LUMEN_API_KEY` | Lumen API authentication key | `your-lumen-api-key` |
| `LUMEN_BASE_URL` | Lumen API base URL | `https://api.lumen.com/v1` |
| `CLIENT_ID` | Azure App Registration Client ID | `12345678-1234-1234-1234-123456789012` |
| `CLIENT_SECRET` | Azure App Registration Client Secret | `your-client-secret` |
| `TENANT_ID` | Azure Tenant ID | `87654321-4321-4321-4321-210987654321` |
| `WORKSPACE_ID` | Microsoft Sentinel Workspace ID | `abcdef12-3456-7890-abcd-ef1234567890` |

## Deployment

### Option 1: Deploy via VS Code

1. Install [Azure Functions Extension](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurefunctions)
2. Right-click the `LumenThreatIntelligenceConnector` folder
3. Select "Deploy to Function App..."
4. Follow the deployment wizard

### Option 2: Deploy via Azure CLI

```bash
# Create resource group
az group create --name rg-lumen-ti --location eastus

# Create storage account
az storage account create --name stalumentitf001 --resource-group rg-lumen-ti --location eastus --sku Standard_LRS

# Create function app
az functionapp create --resource-group rg-lumen-ti --consumption-plan-location eastus \
  --runtime python --runtime-version 3.9 --functions-version 4 \
  --name func-lumen-ti-001 --storage-account stalumentitf001

# Deploy function code
cd "Solutions/Lumen/Data Connectors/LumenThreatIntelligenceConnector"
func azure functionapp publish func-lumen-ti-001
```

### Option 3: Deploy via ARM Template

Deploy using the included ARM template (coming soon).

## Configuration

### 1. Azure App Registration

Create an app registration in Microsoft Entra ID:

```bash
# Create app registration
az ad app create --display-name "Lumen TI Connector"

# Create service principal
az ad sp create --id <app-id>

# Assign Microsoft Sentinel Contributor role
az role assignment create --assignee <app-id> \
  --role "Microsoft Sentinel Contributor" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/<rg-name>/providers/Microsoft.OperationalInsights/workspaces/<workspace-name>"
```

### 2. Function App Settings

Set environment variables in your Function App:

```bash
az functionapp config appsettings set --name func-lumen-ti-001 --resource-group rg-lumen-ti \
  --settings \
  LUMEN_API_KEY="your-lumen-api-key" \
  LUMEN_BASE_URL="https://api.lumen.com/v1" \
  CLIENT_ID="12345678-1234-1234-1234-123456789012" \
  CLIENT_SECRET="your-client-secret" \
  TENANT_ID="87654321-4321-4321-4321-210987654321" \
  WORKSPACE_ID="abcdef12-3456-7890-abcd-ef1234567890"
```

## Scheduling

The function runs every 6 hours by default. Modify the schedule in `function.json`:

```json
{
  "schedule": "0 0 */6 * * *"  // Every 6 hours
}
```

Schedule examples:
- `"0 0 */4 * * *"` - Every 4 hours
- `"0 0 8,20 * * *"` - Twice daily at 8 AM and 8 PM
- `"0 0 0 * * *"` - Once daily at midnight

## API Details

### Lumen API Flow

1. **POST** to `{LUMEN_BASE_URL}/threat-intelligence/download`
   ```json
   Headers: {
     "Authorization": "Bearer {LUMEN_API_KEY}",
     "Content-Type": "application/json"
   }
   ```

2. **GET** presigned URL from response
   ```json
   Response: {
     "downloadUrl": "https://presigned-url..."
   }
   ```

3. **Extract** `stixobjects` array from downloaded data

### Microsoft Sentinel STIX Objects API

- **Endpoint**: `https://api.ti.sentinel.azure.com/workspaces/{workspaceId}/threat-intelligence-stix-objects:upload`
- **API Version**: `2024-02-01-preview`
- **Rate Limits**: 100 objects per request, 100 requests per minute
- **Request Format**:
  ```json
  {
    "sourcesystem": "Lumen",
    "stixobjects": [...]
  }
  ```

## Monitoring

Monitor the function through:

1. **Azure Portal** - Function App > Functions > LumenThreatIntelligenceConnector > Monitor
2. **Application Insights** - Detailed telemetry and performance metrics
3. **Log Analytics** - Custom queries on function logs

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify `CLIENT_ID`, `CLIENT_SECRET`, and `TENANT_ID`
   - Ensure app registration has Microsoft Sentinel Contributor role

2. **Lumen API Errors**
   - Verify `LUMEN_API_KEY` and `LUMEN_BASE_URL`
   - Check Lumen API rate limits and quotas

3. **Rate Limiting**
   - Function includes built-in rate limiting
   - Monitor for 429 responses and adjust timing if needed

4. **Large Dataset Issues**
   - Function processes data in batches of 100 objects
   - Timeout is set to 5 minutes for large downloads

### Logs

Check function logs for detailed error information:

```bash
az functionapp logs tail --name func-lumen-ti-001 --resource-group rg-lumen-ti
```

## Security Considerations

- **Secrets Management**: Store sensitive values in Azure Key Vault
- **Managed Identity**: Consider using managed identity instead of client secrets
- **Network Security**: Deploy in a VNet for enhanced security
- **Access Control**: Use least-privilege access for the app registration

## Performance

- **Processing Rate**: ~10,000 objects per minute (respecting API limits)
- **Memory Usage**: Optimized for large datasets with streaming processing
- **Error Recovery**: Automatic retry with exponential backoff

## Support

For issues and questions:
1. Check the function logs in Azure Portal
2. Review Microsoft Sentinel TI connector documentation
3. Contact your Lumen API support team for API-related issues
