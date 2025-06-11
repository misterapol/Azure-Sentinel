# Lumen-ThreatIntelligenceImport

## Overview
This playbook serves as a batch receiver for threat intelligence indicators from Lumen's API into Microsoft Sentinel. It follows modern best practices by implementing a batching pattern for efficient indicator processing.

## Prerequisites
- Microsoft Sentinel workspace with Threat Intelligence solution installed
- A separate Logic App that feeds indicators to this batch receiver

## Deployment

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FAzure%2FAzure-Sentinel%2Fmaster%2FSolutions%2FLumen%2FPlaybooks%2FLumen-ThreatIntelligenceImport%2Fazuredeploy.json)

## Post-Deployment Configuration

1. **Grant Sentinel Access**: Add Logic App managed identity as 'Microsoft Sentinel Contributor'
2. **Configure Feeder**: Set up a separate Logic App to send indicators to this batch receiver

## Support
For issues or questions, contact Lumen support at support@lumen.com

