# Lumen Threat Intelligence Solution for Microsoft Sentinel

This solution integrates Lumen's threat intelligence data with Microsoft Sentinel using modern Azure-Sentinel patterns for efficient and scalable threat intelligence ingestion.

## Overview

The Lumen Threat Intelligence solution provides automated ingestion of threat intelligence indicators from Lumen's threat intelligence feeds into Microsoft Sentinel. The solution follows modern batch processing patterns similar to other enterprise threat intelligence connectors like Recorded Future, ensuring reliable and efficient data ingestion.

## Architecture

The solution uses a simplified architecture pattern:

- **Batch Receiver Pattern**: Uses Logic Apps with batch triggers to efficiently process threat intelligence indicators in batches
- **Managed Identity Authentication**: Eliminates credential management complexity by using Azure managed identities
- **Modern API Integration**: Leverages the V2 Threat Intelligence Upload Indicators API for optimal performance
- **Minimal Dependencies**: Reduced complexity by eliminating storage accounts and key vault dependencies

## Features

- **Automated Threat Intelligence Ingestion**: Processes Lumen threat intelligence indicators automatically
- **Batch Processing**: Efficiently handles large volumes of indicators using batch triggers
- **Managed Identity Security**: Secure authentication without manual credential management
- **Retry Logic**: Built-in retry policies for reliable data ingestion
- **Modern API Support**: Uses the latest V2 Threat Intelligence APIs

## Components

### Playbooks

- **Lumen-ThreatIntelligenceImport**: Batch receiver Logic App that processes threat intelligence indicators in batches and uploads them to Microsoft Sentinel
- **Lumen-IP-IndicatorImport**: Logic App that fetches IP threat intelligence from Lumen's API using an inline custom connector and sends indicators to the batch processor

## Prerequisites

Before deploying this solution, ensure you have:

1. **Microsoft Sentinel Workspace**: A Microsoft Sentinel workspace with the Threat Intelligence solution enabled
2. **Lumen API Access**: Valid Lumen API key with access to threat intelligence endpoints
3. **Appropriate Permissions**: Rights to deploy Logic Apps, custom connectors, and create managed identity connections in your Azure subscription

## Deployment

⚠️ **Important**: Components must be deployed in the following order:

### Step 1: Deploy Batch Receiver

Deploy the threat intelligence batch receiver:

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FAzure%2FAzure-Sentinel%2Fmaster%2FSolutions%2FLumen%2FPlaybooks%2FLumen-ThreatIntelligenceImport%2Fazuredeploy.json)

### Step 2: Deploy IP Indicator Import

Deploy the IP indicator import playbook (includes inline custom connector):

[![Deploy IP Import](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FAzure%2FAzure-Sentinel%2Fmaster%2FSolutions%2FLumen%2FPlaybooks%2FLumen-IP-IndicatorImport%2Fazuredeploy.json)

### Manual Deployment

1. **Deploy Batch Receiver**: Navigate to `Playbooks/Lumen-ThreatIntelligenceImport` and deploy the ARM template  
2. **Deploy IP Import**: Navigate to `Playbooks/Lumen-IP-IndicatorImport` and deploy the ARM template (includes inline custom connector)
3. Provide the required parameters for each deployment

### Post-Deployment Configuration

After deployment:

1. **Configure API Connection**: Open the Lumen-IP-IndicatorImport playbook and configure the Lumen API connection with your API key
2. **Verify Batch Processing**: The batch receiver Logic App will be created with a batch trigger named "LumenImportBatch"
3. **Test Integration**: Run the IP import playbook manually to verify the integration is working

## Usage

### Sending Indicators

To send threat intelligence indicators to the batch receiver, use the batch trigger endpoint. The Logic App will process indicators in batches of 100 or every 4 hours, whichever comes first.

### Monitoring

Monitor the Logic App execution through:
- Azure Portal Logic Apps monitoring
- Microsoft Sentinel Workbooks
- Azure Monitor Logs

## Configuration

### Batch Processing

The solution is configured with the following batch settings:
- **Batch Size**: 100 indicators per batch
- **Time Interval**: 4 hours maximum wait time
- **Trigger Name**: LumenImportBatch

### API Integration

The playbook uses the V2 Threat Intelligence Upload Indicators API:
- Endpoint: `/V2/ThreatIntelligence/{WorkspaceID}/UploadIndicators/`
- Authentication: Managed Identity
- Retry Policy: Configured for reliable ingestion

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure the Logic App's managed identity has appropriate permissions on the Sentinel workspace
2. **API Errors**: Verify the WorkspaceID parameter is correct
3. **Batch Processing**: Check batch trigger configuration if indicators aren't being processed

### Monitoring and Logs

- Review Logic App run history in the Azure Portal
- Check Microsoft Sentinel Threat Intelligence blade for ingested indicators
- Use Azure Monitor for detailed logging and monitoring

## Support

For issues related to:
- **Azure Sentinel Integration**: Refer to Microsoft Sentinel documentation
- **Logic Apps**: Check Azure Logic Apps documentation
- **Lumen Threat Intelligence**: Contact Lumen support

## Version History

- **v2.0**: Simplified architecture using batch receiver pattern
- **v1.0**: Initial release with complex workflow pattern

## Contributing

This solution follows Azure Sentinel community standards. For contributions or improvements, please follow the Azure Sentinel repository contribution guidelines.

## License

This solution is provided under the MIT License. See the main Azure Sentinel repository for full license details.