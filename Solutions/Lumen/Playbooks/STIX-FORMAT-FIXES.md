# Lumen STIX Format - Updated Troubleshooting Guide

## 🎯 Discovery: Lumen API Returns STIX Format

Based on your testing, the Lumen API returns this structure:
```json
{
    "sourcesystem": "Lumen",
    "stixobjects": [
        {
            "pattern": "[ipv4-addr:value = '57.151.105.154']",
            "confidence": "78",
            "description": "scan, attack",
            "id": "indicator--f6afc86d-9d0d-55d4-a477-00bd51d96d86",
            "type": "indicator",
            "pattern_type": "stix",
            "pattern_version": "2.1",
            "valid_from": "2025-06-11 00:00:00",
            "valid_until": "2025-06-18 00:00:00"
        }
    ]
}
```

## ✅ Critical Fixes Applied

### 1. **Correct JSON Parsing Logic**
- **BEFORE**: Used `split(string(body('Get_Chunk')), '\n')` (wrong - tried to split by newlines)
- **AFTER**: Used `json(string(body('Get_Chunk')))['stixobjects']` (correct - extracts STIX objects array)

### 2. **Improved Range Request Handling**
- **Enhanced error handling**: Now handles both succeeded and failed range requests
- **Better range formatting**: Uses proper conditional formatting for initial vs subsequent chunks
- **Added success validation**: Checks for HTTP 206 status code

### 3. **STIX Object Processing**
- **Log_Line_Content**: Now logs STIX indicator properties (id, type, pattern)
- **Check_Valid_JSON**: Validates STIX indicator objects instead of raw JSON strings
- **Send_to_Batch**: Sends parsed STIX objects directly (no additional JSON parsing needed)

### 4. **Enhanced Debugging**
- **requestSucceeded**: Shows if range request worked (should be HTTP 206)
- **Better object inspection**: Shows actual STIX indicator properties

## ✅ Enhanced Error Handling (Latest Update)

### 4. **Robust Conditional JSON Parsing**
- **BEFORE**: Direct JSON parsing that could fail silently
- **AFTER**: Enhanced conditional logic that validates JSON structure before parsing

```json
"Parse_JSON_Lines": {
    "type": "Compose",
    "inputs": "@if(and(greater(length(string(body('Get_Chunk'))), 10), contains(string(body('Get_Chunk')), 'stixobjects'), startsWith(trim(string(body('Get_Chunk'))), '{')), json(string(body('Get_Chunk')))['stixobjects'], createArray('NO_DATA'))"
}
```

### 5. **Enhanced Debug Information**
- **dataType**: Shows whether response contains STIX objects or is empty
- **lineCount**: Number of STIX objects found
- **firstFewLines**: Sample of parsed data for validation
- **hasValidLines**: Boolean indicating if valid data exists

### 6. **Robust Condition Checking**
- **Multi-layer validation**: Checks length, content, and JSON structure
- **Safe JSON parsing**: Only attempts parsing when structure is valid
- **Error Recovery**: Gracefully handles partial chunks and malformed responses

## 🔍 Latest Debug Output Format

### Debug_Parsed_Lines (Enhanced):
```json
{
  "lineCount": 5,
  "firstFewLines": [
    {"id": "indicator--123", "type": "indicator", "pattern": "[ipv4-addr:value = '1.2.3.4']"},
    {"id": "indicator--456", "type": "indicator", "pattern": "[domain-name:value = 'evil.com']"}
  ],
  "hasValidLines": true,
  "dataType": "STIX_OBJECTS"
}
```

### Empty/Error Scenario:
```json
{
  "lineCount": 1,
  "firstFewLines": ["NO_DATA"],
  "hasValidLines": false,
  "dataType": "NO_DATA"
}
```

## 🚨 Range Request Issue Resolution

The **"starting range index mismatch"** error occurred because:
1. First request fails due to template error
2. Offset still increments to 1048576
3. Second request asks for wrong range

**Fix applied**:
- Enhanced error handling to catch failed requests
- Improved range header formatting
- Added request success validation

## 🎯 Expected Flow After Fixes

1. **Get_Chunk**: HTTP GET with proper range header → HTTP 206 response
2. **Debug_Chunk_Response**: Shows successful range request (statusCode: 206)
3. **Parse_JSON_Lines**: Extracts `stixobjects` array from JSON response
4. **Debug_Parsed_Lines**: Shows array of STIX indicator objects
5. **Process_Each_Line**: Iterates through each STIX indicator
6. **Log_Line_Content**: Shows individual STIX indicator properties
7. **Check_Valid_JSON**: Validates each indicator has required properties
8. **Send_to_Batch**: Sends STIX indicator to import playbook

## 📊 Key Improvements

| Component | Before | After |
|-----------|--------|-------|
| **Data Format** | Expected JSONL (wrong) | STIX objects array (correct) |
| **Parsing** | Split by newlines | Extract stixobjects array |
| **Validation** | Check for JSON brackets | Check for indicator type |
| **Range Requests** | Basic error handling | Enhanced success validation |
| **Debugging** | Generic line info | STIX-specific properties |

## 🚀 Next Test Results Expected

With these fixes, you should see:
- ✅ **No more template errors** in Debug_Chunk_Response
- ✅ **Successful range requests** (HTTP 206 responses)
- ✅ **STIX objects extracted** properly in Debug_Parsed_Lines
- ✅ **Individual indicators processed** in Log_Line_Content
- ✅ **Batch messages sent** to import playbook
- ✅ **No more offset misalignment** errors

The collector should now properly handle the Lumen STIX format and successfully process threat intelligence indicators! 🎯

## 📊 Monitoring the Enhanced Solution

Check these debug outputs in sequence:
1. **Debug_Chunk_Response** → API working? Contains 'stixobjects'?
2. **Debug_Parsed_Lines** → JSON parsing working? Data extracted?
3. **Check_Has_Data** → Valid STIX objects present?
4. **Log_Line_Content** → Individual indicators structured correctly?
5. **Send_to_Batch** → Batch sending successful?

The Try-Catch approach ensures the workflow continues even with parsing errors, providing clear diagnostic information for troubleshooting! 🔧
