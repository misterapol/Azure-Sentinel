# Changelog

## v2.1.0 - 2025-06-12

### Fixed
- Resolved "BadRequest" error caused by buffer size limitations (104857600 bytes) when processing large files
- Implemented chunked download approach using HTTP Range headers
- Fixed ARM template validation errors in several conditional actions (changed from "Condition" to "If" type)
- Fixed duplicate action names that caused template validation failures
- Moved variable initialization actions outside of conditional and Until actions to resolve "InvalidVariableInitialization" errors
- Changed nested initialize variable actions to set variable actions or Compose actions within Until loop
- Fixed invalid action references in runAfter properties
- Replaced InitializeVariable with Compose action for CreateDummyVariable
- Initialized all variables at the top level of the workflow
- Corrected dependency structure in the "HandleUploadFailure" action
- Enhanced error handling for HTTP status codes in the download process
- Fixed reference errors to non-existent actions ("Step3_StreamAndProcessLargeFile")
- Improved chunked download approach to handle partial content (206) and end-of-file (416) responses
- Fixed remaining variable initialization issues to ensure all variables are properly initialized at the top level
- Fixed self-reference issue in "MergeIndicatorArrays" and "MergeFinalIndicatorArrays" actions by replacing union() with concat()

### Changed
- Replaced single file download with chunked approach using HTTP Range headers
- Each chunk is now downloaded as 5MB (5242880 bytes) to stay well under buffer limitations
- Reorganized workflow to use collected data through the "AllIndicators" variable
- Updated data processing flow to accommodate chunked downloads
- Enhanced logging for better troubleshooting and visibility
- Improved range calculation with dedicated variables for better readability and maintenance
- Updated response handling to gracefully handle different HTTP status codes

### Added
- Added HEAD request to get file metadata before chunking
- Added batch processing tracking with intelligent resume capability
- Added CHANGELOG.md to track modifications
- Added detailed file metadata logging with estimated chunks needed
- Added comprehensive troubleshooting section to the documentation
- Added status code-based branching logic to handle various download scenarios
- Added variables to store and calculate range values (ChunkSizeBytes, RangeStart, RangeEnd)
- Added improved error logging with context for each failure mode

### Removed
- Removed the problematic "Step3_StreamAndProcessLargeFile" action that was causing the buffer limitation error
- Eliminated direct references to parsed JSON in favor of the incremental chunked approach
