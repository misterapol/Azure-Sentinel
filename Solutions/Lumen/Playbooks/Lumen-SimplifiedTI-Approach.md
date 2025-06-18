# Simplified Lumen Threat Intelligence Approach

## Recommended Architecture

### Two-Playbook Pattern (Like Recorded Future)

1. **Lumen-IndicatorCollector** - Handles API calls and data chunking
2. **Lumen-ThreatIntelligenceImport** - Handles batch upload to Sentinel

### Key Simplifications

#### 1. Avoid Large File Processing in Logic Apps
- Instead of downloading the entire 170MB file, use pagination if Lumen API supports it
- If pagination isn't available, download smaller chunks using HTTP Range headers
- Process chunks sequentially rather than trying to load entire file

#### 2. Use Proven Upload Pattern
```json
{
  "type": "ApiConnection",
  "inputs": {
    "body": {
      "indicators": "@body('Select')",
      "sourcesystem": "Lumen"
    },
    "host": {
      "connection": {
        "name": "@parameters('$connections')['azuresentinel']['connectionId']"
      }
    },
    "method": "post",
    "path": "/V2/ThreatIntelligence/{WorkspaceID}/UploadIndicators/",
    "retryPolicy": {
      "count": 10,
      "interval": "PT20S",
      "maximumInterval": "PT1H",
      "minimumInterval": "PT10S",
      "type": "exponential"
    }
  }
}
```

#### 3. Simplified Flow
1. **Collector Playbook**:
   - Get presigned URL from Lumen API
   - Use HTTP GET with Range headers to fetch small chunks (1-5MB each)
   - Parse JSON chunks and extract indicators
   - Send indicators to batch processor in groups of 50-100

2. **Import Playbook**:
   - Receive batched indicators
   - Transform to required format if needed
   - Upload to Sentinel using proven connector pattern

### Alternative: Use Azure Functions
If Logic Apps continue to have issues with large files, consider the CrowdStrike approach:
- Deploy Azure Function to handle large file processing
- Function can handle the 170MB file more reliably
- Logic App just triggers the function and handles results

## Implementation Steps

1. Start with a minimal viable playbook that handles just a small subset of data
2. Test the upload mechanism thoroughly with small batches
3. Gradually increase batch sizes and add complexity
4. Add error handling and retry logic only after basic flow works

## Key Lessons from Other Providers

- Keep upload logic separate from collection logic
- Use proven connector patterns rather than custom HTTP calls
- Batch processing is essential for performance and reliability
- Start simple and add complexity incrementally
