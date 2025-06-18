# Lumen Simplified TI Integration - Deployment Guide

## Overview
This simplified approach replaces the complex 170MB file processing Logic App with a two-playbook solution using proven patterns from other threat intelligence providers.

## ✅ Fixed Issues
- **Managed Identity Authentication**: Added proper MSI configuration for Azure Sentinel connection
- **Connection Parameters**: Fixed authentication property in connection setup
- **Role Assignments**: Created separate template for granting Logic App permissions

## 🚀 Deployment Steps

### Prerequisites
1. Azure Sentinel workspace (Log Analytics workspace with Sentinel enabled)
2. Resource group for deployment
3. Lumen API key
4. Contributor access to the resource group
5. Security Admin or equivalent permissions on the Sentinel workspace

### Step 1: Deploy the Import Playbook
```bash
# Deploy the threat intelligence import playbook
az deployment group create \
  --resource-group <your-resource-group> \
  --template-file Lumen-ThreatIntelligenceImport-Simple/azuredeploy.json \
  --parameters PlaybookName="Lumen-ThreatIntelligenceImport-Simple" \
               WorkspaceID="<your-sentinel-workspace-id>"
```

### Step 2: Deploy the Collector Playbook
```bash
# Deploy the indicator collector playbook
az deployment group create \
  --resource-group <your-resource-group> \
  --template-file Lumen-IndicatorCollector-Simple/azuredeploy.json \
  --parameters PlaybookName="Lumen-IndicatorCollector-Simple" \
               LumenAPIKey="<your-lumen-api-key>" \
               BatchProcessorName="Lumen-ThreatIntelligenceImport-Simple"
```

### Step 3: Grant Sentinel Permissions
```bash
# Grant the Logic App managed identity access to Sentinel
az deployment group create \
  --resource-group <your-resource-group> \
  --template-file Lumen-ThreatIntelligenceImport-Simple/roleAssignment.json \
  --parameters LogicAppName="Lumen-ThreatIntelligenceImport-Simple" \
               WorkspaceResourceId="/subscriptions/<subscription-id>/resourceGroups/<workspace-rg>/providers/Microsoft.OperationalInsights/workspaces/<workspace-name>"
```

### Step 4: Enable the Playbooks
```bash
# Enable the collector playbook (this will start the 6-hour recurrence)
az logic workflow update \
  --resource-group <your-resource-group> \
  --name "Lumen-IndicatorCollector-Simple" \
  --state "Enabled"

# The import playbook is automatically enabled via batch trigger
```

## 🔧 Configuration Details

### Managed Identity Authentication
- **Connection Type**: Azure Sentinel API connection with Managed Service Identity
- **Authentication**: System-assigned managed identity (no secrets required)
- **Permissions**: Microsoft Sentinel Contributor role on the workspace

### Batch Processing Configuration
- **Batch Name**: "LumenImportBatch" (consistent between playbooks)
- **Batch Size**: 100 indicators per batch
- **Timeout**: 5 minutes (processes smaller batches faster)
- **Chunk Size**: 1MB (collector processes file in manageable chunks)

### Error Handling & Resilience
- **Retry Policy**: Exponential backoff (10 retries, up to 1 hour)
- **Partial Processing**: Handles incomplete chunks gracefully
- **API Rate Limiting**: 2-second delays between chunk requests
- **Connection Resilience**: Managed identity eliminates secret expiration issues

## 🔍 Monitoring & Troubleshooting

### Key Metrics to Monitor
1. **Collector Runs**: Check every 6 hours for successful API calls to Lumen
2. **Batch Processing**: Monitor import playbook for batch trigger frequency
3. **Upload Success**: Verify indicators appear in Sentinel TI within minutes
4. **Error Rates**: Watch for API failures or authentication issues

### Common Issues & Solutions

#### Authentication Errors
```
Error: "The workflow connection parameter 'azuresentinel' is not valid"
```
**Solution**: Ensure role assignment step was completed successfully.

#### Batch Not Triggering
```
Issue: Import playbook not receiving batches
```
**Solution**: Check batch configuration name matches between playbooks ("LumenImportBatch").

#### API Rate Limiting
```
Issue: HTTP 429 responses from Lumen API
```
**Solution**: Current design includes 2-second delays; increase if needed.

### Verification Commands
```bash
# Check Logic App status
az logic workflow show \
  --resource-group <your-resource-group> \
  --name "Lumen-IndicatorCollector-Simple" \
  --query "state"

# Check role assignment
az role assignment list \
  --assignee <logic-app-principal-id> \
  --scope "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.OperationalInsights/workspaces/<workspace>"

# View recent runs
az logic workflow list-runs \
  --resource-group <your-resource-group> \
  --name "Lumen-IndicatorCollector-Simple" \
  --top 5
```

## 📊 Performance Improvements

| Metric | Original Complex Solution | Simplified Solution |
|--------|---------------------------|-------------------|
| File Processing | 170MB single file | 1MB chunks |
| Memory Usage | High (entire file in memory) | Low (chunked processing) |
| Error Recovery | Restart entire process | Resume from failed chunk |
| Scalability | Single-threaded | Parallel batch processing |
| Maintenance | Complex STIX logic | Simple JSON pass-through |
| Authentication | Manual secret management | Managed identity |

## 🎯 Success Criteria

1. **Deployment**: Both playbooks deploy without errors
2. **Authentication**: Managed identity connection works
3. **Processing**: File chunks processed within reasonable time
4. **Upload**: Indicators appear in Sentinel TI portal
5. **Reliability**: No authentication failures, minimal API errors
6. **Performance**: Processing completes faster than original 170MB approach

## 🔄 Next Steps After Deployment

1. **Monitor First Run**: Watch collector's first execution end-to-end
2. **Validate Data**: Check Sentinel TI portal for Lumen indicators
3. **Performance Tuning**: Adjust batch sizes or timing if needed
4. **Alerting**: Set up Logic App failure alerts
5. **Scaling**: Consider increasing frequency if data freshness requirements change

---

**Note**: This simplified approach eliminates the complexity of STIX bundle creation and focuses on reliable, proven patterns used by other major threat intelligence providers in the Azure Sentinel ecosystem.
