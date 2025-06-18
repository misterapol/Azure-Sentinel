# Lumen Collector Troubleshooting Guide

## Issue: Process_Each_Line Action Being Skipped

### Root Cause Analysis
The `Process_Each_Line` action is being skipped because either:
1. The API response is empty or invalid
2. The `split()` function isn't working on the response format
3. The response isn't in the expected text format

### ✅ Enhanced Debugging Applied

#### 1. **Added Comprehensive Response Debugging**
- **Debug_Chunk_Response**: Shows API response details:
  - Status code
  - Response headers  
  - Body type and length
  - First 500 characters of response
- **Debug_Parsed_Lines**: Shows parsing results:
  - Number of lines after split
  - First few lines
  - Whether valid lines exist

#### 2. **Added Safe Data Handling**
- **Parse_JSON_Lines**: Now handles empty responses gracefully
- **Check_Has_Data**: Validates data exists before processing
- **Process_Each_Line**: Only runs when actual data is present

#### 3. **Improved Error Flow**
- Actions now continue even if some steps are skipped
- `Calculate_New_Offset` runs after `Check_Has_Data` regardless of outcome
- Prevents entire workflow from failing on empty chunks

### 🔍 New Debugging Information Available

#### Debug_Chunk_Response Output
```json
{
  "statusCode": 200,
  "headers": {"content-type": "application/json"},
  "bodyType": "String",
  "bodyLength": 1024,
  "firstChars": "{'indicator':'192.168.1.1',...}"
}
```

#### Debug_Parsed_Lines Output  
```json
{
  "lineCount": 10,
  "firstFewLines": ["line1", "line2", "line3"],
  "hasValidLines": true
}
```

### 🛠️ Common API Response Issues

#### Issue 1: Empty Response
**Symptoms**: `bodyLength: 0`, `firstChars: "EMPTY_RESPONSE"`
**Causes**: 
- API endpoint returns no data
- Range request not supported
- API key authentication failed

#### Issue 2: Wrong Content Type
**Symptoms**: `bodyType` not String, unexpected `firstChars`
**Causes**:
- API returns binary data instead of text
- API returns HTML error page
- API returns different format than expected

#### Issue 3: Single JSON vs JSONL
**Symptoms**: `lineCount: 1`, single object in `firstFewLines`
**Causes**:
- API returns single JSON object instead of JSONL
- Need to parse as single object, not split by lines

#### Issue 4: Non-Newline Delimited
**Symptoms**: `lineCount: 1`, very long single line
**Causes**:
- API uses different delimiter (comma, space, etc.)
- Need different split strategy

### 🔧 Debugging Steps

#### Step 1: Check API Response Format
1. Look at `Debug_Chunk_Response` output
2. Check `statusCode` (should be 200 or 206)
3. Check `bodyLength` (should be > 0)
4. Check `firstChars` to see actual data format

#### Step 2: Analyze Data Structure  
1. Look at `Debug_Parsed_Lines` output
2. Check `lineCount` (should be > 1 for JSONL)
3. Check `firstFewLines` to see line structure
4. Verify `hasValidLines` is true

#### Step 3: Verify JSON Format
1. If lines look like JSON objects, proceed to `Log_Line_Content`
2. If single object, may need to modify parsing approach
3. If not JSON, may need different data handling

## ✅ Latest Enhancement: Try-Catch JSON Parsing

### Issue: JSON Parsing Failures in Chunked Responses
When processing large files in chunks, the response might be:
- **Incomplete JSON**: Chunk ends in middle of JSON object
- **Missing Properties**: 'stixobjects' property not present
- **Invalid Format**: Response not valid JSON structure

### Solution: Robust Try-Catch Approach

#### 1. **Enhanced Parse_JSON_Lines Action**
```json
"Parse_JSON_Lines": {
    "type": "Try",
    "actions": {
        "Try_Parse_STIX": {
            "type": "Compose", 
            "inputs": "@json(string(body('Get_Chunk')))['stixobjects']"
        }
    },
    "catch": {
        "actions": {
            "Set_Parse_Error": {
                "type": "Compose",
                "inputs": "@createArray('PARSE_ERROR')"
            }
        }
    }
}
```

#### 2. **Improved Debug Information**
- **parseSucceeded**: Boolean indicating if JSON parsing worked
- **parsedData**: Either STIX objects array or error indicator
- **Enhanced error tracking**: Clear distinction between parse errors and empty data

#### 3. **Robust Condition Logic**
- **Check_Has_Data**: Now validates parse success AND data presence
- **Graceful degradation**: Workflow continues even with parsing errors
- **Better error visibility**: Parse errors clearly identified in debug output

### 🎯 Debugging the Enhanced Solution

#### Step 1: Check Debug_Chunk_Response
Look for:
- ✅ `statusCode: 200` or `206` (partial content)
- ✅ `containsStixObjects: true`
- ✅ `bodyLength > 0`
- ✅ `firstChars` showing JSON structure

#### Step 2: Analyze Debug_Parsed_Lines
Look for:
- ✅ `parseSucceeded: true` 
- ✅ `lineCount > 0`
- ✅ `hasValidLines: true`
- ✅ `firstFewLines` showing actual STIX indicators

#### Step 3: Verify Data Processing
- ✅ `Check_Has_Data` condition should evaluate to true
- ✅ `Process_Each_Line` should execute with STIX objects
- ✅ `Log_Line_Content` should show indicator properties
- ✅ `Send_to_Batch` should successfully send to batch processor

### 🔧 Common Scenarios & Solutions

#### Scenario 1: Parse Error (Chunked JSON)
```json
"Debug_Parsed_Lines": {
    "parseSucceeded": false,
    "parsedData": ["PARSE_ERROR"],
    "lineCount": 0,
    "hasValidLines": false
}
```
**Solution**: The chunk broke in middle of JSON. Next chunk should contain complete JSON.

#### Scenario 2: Empty Response
```json
"Debug_Chunk_Response": {
    "statusCode": 416,
    "bodyLength": 0,
    "containsStixObjects": false
}
```
**Solution**: Reached end of file. Logic should set ProcessedCount to -1.

#### Scenario 3: Different JSON Structure
```json
"Debug_Chunk_Response": {
    "statusCode": 200,
    "containsStixObjects": false,
    "firstChars": "{\"indicators\":[...]}
}
```
**Solution**: API changed format. Update parsing logic to match new structure.

### 📊 Expected Success Flow

1. **Get_Chunk**: HTTP 200/206 with valid response
2. **Debug_Chunk_Response**: Shows JSON with 'stixobjects'
3. **Parse_JSON_Lines**: Try succeeds, extracts STIX array
4. **Debug_Parsed_Lines**: Shows parseSucceeded=true, lineCount>0
5. **Check_Has_Data**: Evaluates to true
6. **Process_Each_Line**: Iterates through STIX objects
7. **Log_Line_Content**: Shows indicator details (id, type, pattern)
8. **Send_to_Batch**: Successfully sends to batch processor

This enhanced approach provides much better error handling and debugging visibility! 🚀
