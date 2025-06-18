# Lumen Smart Chunking Strategy

## 🎯 Problem with Traditional Byte-Range Chunking

When processing large STIX files using arbitrary byte ranges (e.g., 1MB chunks), we face several issues:

1. **Broken JSON**: Chunks can split in the middle of JSON objects
2. **Incomplete Indicators**: STIX indicators get cut in half
3. **Complex Parsing**: Need to handle partial data and reconstruction

## 🧠 Smart Indicator-Aware Chunking Solution

### Core Insight
Since we know the structure of Lumen STIX data:
- **First chunk**: Contains `{"sourcesystem": "Lumen", "stixobjects": [...]}`
- **Subsequent chunks**: Raw indicator objects in the middle of the array
- **Each indicator**: Starts with `"pattern"` and ends with `"valid_until"`

### Strategy Implementation

#### 1. **Chunk Type Detection**
```json
"Debug_Chunk_Response": {
    "containsStixObjects": "true/false - First chunk with header",
    "startsWithPattern": "true/false - Middle chunk with indicators", 
    "endsWithValidUntil": "true/false - Contains complete indicators"
}
```

#### 2. **Smart Parsing Logic**
- **First Chunk**: Parse as complete JSON → `json(body)['stixobjects']`
- **Middle Chunks**: Extract complete indicators up to last `valid_until`
- **Incomplete Chunks**: Skip and adjust offset

#### 3. **Intelligent Offset Calculation**
```
IF first_chunk:
    next_offset = current_offset + chunk_size
ELSE IF contains_complete_indicators:
    last_indicator_end = position_of_last("valid_until") + 25
    next_offset = current_offset + last_indicator_end  
ELSE:
    next_offset = current_offset + chunk_size  // fallback
```

## 🔍 Chunk Type Scenarios

### Scenario 1: First Chunk (Offset = 0)
```json
{
    "sourcesystem": "Lumen",
    "stixobjects": [
        {
            "pattern": "[ipv4-addr:value = '1.2.3.4']",
            "confidence": "78",
            "valid_until": "2025-06-18 00:00:00"
        },
        {
            "pattern": "[ipv4-addr:value = '5.6.7.8']",
            "confidence": "85", 
            // chunk ends here - might be incomplete
```

**Handling**: Parse as JSON, extract `stixobjects` array, process complete indicators only.

### Scenario 2: Middle Chunk (Offset > 0)
```json
        },
        {
            "pattern": "[domain-name:value = 'evil.com']",
            "confidence": "90",
            "valid_until": "2025-06-20 00:00:00"
        },
        {
            "pattern": "[ipv4-addr:value = '9.10.11.12']",
            // chunk ends here - incomplete indicator
```

**Handling**: 
1. Find last complete indicator (ends with `valid_until`)
2. Extract everything up to that point
3. Parse as JSON array
4. Calculate next offset to start after the complete indicator

### Scenario 3: End of File
```json
        {
            "pattern": "[ipv4-addr:value = '13.14.15.16']",
            "confidence": "75",
            "valid_until": "2025-06-25 00:00:00"
        }
    ]
}
```

**Handling**: Process remaining complete indicators, detect end condition.

## 🚀 Benefits of Smart Chunking

### ✅ **Data Integrity**
- Never processes incomplete indicators
- Maintains JSON structure validity
- Ensures all indicators are complete

### ✅ **Performance Optimization**
- Processes maximum complete indicators per chunk
- Minimizes API calls by intelligent offset calculation
- Reduces memory usage compared to full-file loading

### ✅ **Error Resilience**
- Handles various chunk boundary scenarios
- Graceful degradation for malformed responses
- Clear debugging information for each chunk type

### ✅ **Batching Efficiency**
- Sends complete, valid indicators to batch processor
- Optimal batch sizes based on actual indicator count
- No partial data reconstruction needed

## 🔧 Implementation Details

### Parse_Complete_Indicators Logic
```javascript
IF chunk.contains("stixobjects"):
    // First chunk - parse as complete JSON
    return json(chunk)["stixobjects"]
ELSE IF chunk.starts_with_pattern():
    // Middle chunk - extract complete indicators
    last_valid_until_pos = lastIndexOf(chunk, "valid_until")
    complete_data = substring(chunk, 0, last_valid_until_pos + 25)
    return json("[" + complete_data + "]")
ELSE:
    return ["NO_DATA"]
```

### Smart Offset Calculation
```javascript
IF first_chunk:
    next_offset = current_offset + chunk_size
ELSE IF has_complete_indicators:
    indicator_end = lastIndexOf(chunk, "valid_until") + 25
    next_offset = current_offset + indicator_end
ELSE:
    next_offset = current_offset + chunk_size  // skip malformed chunk
```

## 🎯 Expected Outcomes

1. **100% Data Integrity**: No lost or partial indicators
2. **Optimal Chunking**: Process maximum indicators per API call
3. **Robust Error Handling**: Graceful handling of edge cases
4. **Clear Debugging**: Visibility into chunk types and processing decisions
5. **Efficient Batching**: Complete indicators ready for Sentinel import

This approach transforms the chunking challenge from "arbitrary byte splitting" to "intelligent indicator boundary detection" - ensuring we always work with complete, valid STIX indicators! 🎉
