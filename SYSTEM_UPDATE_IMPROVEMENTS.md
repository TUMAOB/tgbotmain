# System Update & Backup Improvements

## Overview
Enhanced the system update and backup functionality with progress tracking, automatic restart script generation, and backup ZIP file downloads.

## Changes Made

### 1. System Manager (`system_manager.py`)

#### Progress Tracking
- **`download_github_repo()`**: Added `progress_callback` parameter
  - Reports download progress (0-80%)
  - Shows connection status, download size, and extraction progress
  - Callback format: `callback(stage, percent, message)`

- **`apply_system_update()`**: Added `progress_callback` parameter
  - Reports backup creation (0-20%)
  - Reports file updates (25-70%)
  - Reports completion (90%)
  - Shows which files are being updated in real-time

#### Restart Script Generation
- **`create_restart_script()`**: New function
  - Creates `restart_bot.sh` bash script
  - Automatically finds and stops the bot process
  - Waits for graceful shutdown (max 10 seconds)
  - Force kills if necessary
  - Starts bot in background with nohup
  - Returns script path for admin instructions

#### Backup ZIP Creation
- **`create_backup_zip(backup_name)`**: New function
  - Compresses backup directory into ZIP file
  - Uses ZIP_DEFLATED compression
  - Returns ZIP path and size

- **`get_backup_zip_path(backup_name)`**: New function
  - Returns existing ZIP path or creates new one
  - Ensures ZIP is always available for download

- **Modified `create_backup()`**:
  - Automatically creates ZIP file after backup
  - ZIP creation is optional (won't fail backup if it fails)

### 2. Bot Handlers (`auth.py`)

#### GitHub Update Handler (`system_message_handler`)
- **Progress Display**:
  - Shows real-time progress bar (█████░░░░░)
  - Updates every 1.5 seconds to avoid rate limits
  - Displays current operation and percentage
  - Progress stages: download → extract → backup → update

- **Restart Instructions**:
  - Automatically creates restart script after successful update
  - Provides two restart options:
    1. `bash restart_bot.sh` (automated)
    2. `python3 run_production.py` (manual)
  - Shows clear instructions to admin

#### ZIP Update Handler (`system_document_handler`)
- **Progress Display**:
  - Same progress tracking as GitHub updates
  - Shows extraction and update progress
  - Real-time file update notifications

- **Restart Instructions**:
  - Same restart script generation
  - Clear post-update instructions

#### Backup Download Feature
- **New Button**: "📥 Download ZIP" in backup details view
- **Handler**: `system_downloadbackup_` callback
  - Creates ZIP if not exists
  - Shows file size before upload
  - Sends ZIP file to admin via Telegram
  - Handles large files gracefully
  - Error handling for failed uploads

## User Experience Improvements

### System Update Flow
**Before:**
```
⏳ Downloading repository...
⏳ Creating backup and applying update...
✅ System Updated Successfully
⚠️ Please restart manually
```

**After:**
```
⏳ System Update in Progress

Progress: ███░░░░░░░ 30%
Status: Downloading... 245 KB

Progress: ██████░░░░ 60%
Status: Updated: auth.py

Progress: ██████████ 100%
Status: Updated 15 files successfully

✅ System Updated Successfully
📦 Updated 15 files:
• auth.py
• system_manager.py
• core/
...

⚠️ Important: Please restart the bot for changes to take effect.

🔄 Restart Options:
1. Run: `bash restart_bot.sh`
2. Or manually: `python3 run_production.py`
```

### Backup Download Flow
**Before:**
- No download option
- Admin had to manually access server files

**After:**
```
📁 Backup Details

📛 Name: backup_full_20260204_143022
📅 Created: 2026-02-04 14:30:22
📦 Type: full
📊 Items: 25
💾 Size: 2.5 MB

[♻️ Restore This Backup]
[📥 Download ZIP]  ← NEW
[🗑️ Delete Backup]
[⬅️ Back]

→ Click Download ZIP →

⏳ Preparing backup ZIP...
📤 Uploading backup ZIP...
Size: 2.5 MB

✅ Backup ZIP sent successfully!
📁 File: backup_full_20260204_143022.zip
💾 Size: 2.5 MB

[File sent to chat]
```

## Technical Details

### Progress Callback System
```python
def progress_callback(stage: str, percent: int, message: str):
    """
    stage: 'download', 'extract', 'backup', 'update', 'complete'
    percent: 0-100
    message: Human-readable status message
    """
```

### Restart Script Features
- **Process Detection**: Finds bot by process name pattern
- **Graceful Shutdown**: Sends SIGTERM first
- **Timeout Handling**: Waits up to 10 seconds
- **Force Kill**: Uses SIGKILL if needed
- **Background Start**: Uses nohup for persistence
- **Logging**: Redirects output to bot.log

### ZIP Compression
- **Format**: ZIP with DEFLATED compression
- **Structure**: Preserves directory structure
- **Metadata**: Includes backup_metadata.json
- **Size**: Typically 30-50% smaller than directory

## Files Modified
1. `system_manager.py` - Core functionality
2. `auth.py` - Bot handlers and UI

## Files Created
- `restart_bot.sh` - Auto-generated restart script (created on update)
- `backups/<backup_name>.zip` - Backup ZIP files (created on backup)

## Testing Recommendations

### Test System Update
1. Use `/system` command
2. Select "🔄 Update System"
3. Choose "From GitHub URL" or "From ZIP File"
4. Verify progress bar updates in real-time
5. Verify restart script is created
6. Check restart instructions are clear

### Test Backup Download
1. Use `/system` command
2. Select "📂 View Backups"
3. Select any backup
4. Click "📥 Download ZIP"
5. Verify ZIP file is sent to chat
6. Verify ZIP can be extracted and contains all files

### Test Restart Script
1. After system update, locate `restart_bot.sh`
2. Run: `bash restart_bot.sh`
3. Verify bot stops gracefully
4. Verify bot restarts automatically
5. Check `bot.log` for output

## Error Handling
- Progress updates ignore rate limit errors
- ZIP creation failure doesn't fail backup
- Restart script handles missing processes
- Download handles large files gracefully
- All operations have try-catch blocks

## Future Enhancements
- Add progress for backup creation
- Support for Windows restart scripts
- Automatic restart after update (optional)
- Backup scheduling
- Incremental backups
- Cloud backup integration
