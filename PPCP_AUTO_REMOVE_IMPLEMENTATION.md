# PPCP Auto-Remove Bad Sites Implementation

## Overview
Added a toggle switch in the admin settings to control automatic removal of bad PPCP sites.

## Features
- **ON/OFF Toggle**: Admins can enable or disable auto-removal of bad sites
- **Visual Indicator**: Shows 🟢 ON or 🔴 OFF status in the menu
- **Backward Compatible**: Defaults to enabled (existing behavior)
- **Persistent Settings**: Settings saved to `ppcp_auto_remove_settings.json`

## User Interface

### Access Path
```
/admin → ⚙️ Settings → 🔗 PPCP Sites
```

### Menu Display
```
🔗 PPCP Sites

Total sites: X
Auto-Remove Bad Sites: 🟢 ON

Select an option:
[➕ Add Site]
[📋 View Sites]
[➖ Remove Site]
[🗑️ Auto-Remove Bad Sites: 🟢 ON]  ← Click to toggle
[⬅️ Back]
```

## Implementation Details

### Files Modified

#### 1. `/vercel/sandbox/auth.py`
- Added settings file constants:
  - `PPCP_AUTO_REMOVE_SETTINGS_FILE = 'ppcp_auto_remove_settings.json'`
  - `PPCP_AUTO_REMOVE_SETTINGS_LOCK_FILE = 'ppcp_auto_remove_settings.json.lock'`

- Added functions:
  - `load_ppcp_auto_remove_settings()` - Load settings from file
  - `save_ppcp_auto_remove_settings(settings)` - Save settings to file

- Updated `settings_ppcp_sites` action:
  - Loads auto-remove settings
  - Displays current status
  - Shows toggle button

- Added `ppcp_toggle_auto_remove` callback handler:
  - Toggles the enabled/disabled state
  - Saves new state
  - Refreshes menu with updated status

- Updated all PPCP menu returns to show auto-remove status:
  - `ppcp_cancel` handler
  - `ppcp_del_*` handler (after removing a site)

#### 2. `/vercel/sandbox/ppcp/site_manager.py`
- Added import: `import json`
- Added constant: `PPCP_AUTO_REMOVE_SETTINGS_FILE = 'ppcp_auto_remove_settings.json'`
- Added function: `is_auto_remove_enabled()` - Check if auto-remove is enabled
- Modified `add_bad_site()`:
  - Checks `is_auto_remove_enabled()` before removing sites
  - Logs when auto-remove is disabled
  - Returns `False` if disabled (site not removed)

### Settings File Format
```json
{
  "enabled": true
}
```

### Default Behavior
- **Default State**: Enabled (`true`)
- **Backward Compatibility**: If settings file doesn't exist, defaults to enabled
- **File Location**: Project root directory

## How It Works

### When Auto-Remove is ON (🟢)
1. PPCP checker detects a bad site (out of stock, errors, etc.)
2. `add_bad_site()` is called
3. Site is added to `ppcp/badsites.txt`
4. Site is removed from `ppcp/sites.txt`
5. Site will not be used for future checks

### When Auto-Remove is OFF (🔴)
1. PPCP checker detects a bad site
2. `add_bad_site()` is called
3. Function checks `is_auto_remove_enabled()` → returns `False`
4. Site is NOT added to badsites.txt
5. Site is NOT removed from sites.txt
6. Site remains available for checks (admin must manually remove)
7. Log message: "Auto-remove is disabled. Skipping bad site removal for: {url}"

## Testing

### Manual Testing Steps
1. Start the bot: `python3 run_production.py`
2. Send `/admin` command
3. Click "⚙️ Settings"
4. Click "🔗 PPCP Sites"
5. Verify "Auto-Remove Bad Sites: 🟢 ON" button is shown
6. Click the toggle button
7. Verify status changes to "🔴 OFF"
8. Click toggle again
9. Verify status changes back to "🟢 ON"
10. Check that `ppcp_auto_remove_settings.json` file is created

### Automated Testing
All core functionality tested and verified:
- ✓ Default settings (enabled=True)
- ✓ Save disabled state
- ✓ Load disabled state
- ✓ Toggle back to enabled
- ✓ File persistence
- ✓ site_manager integration

## Benefits
1. **Control**: Admins can control when sites are auto-removed
2. **Flexibility**: Can disable auto-remove during testing or troubleshooting
3. **Visibility**: Clear visual indicator of current state
4. **Safety**: Prevents accidental removal of sites when disabled
5. **Backward Compatible**: Existing behavior preserved by default

## Notes
- Settings are stored in JSON format for easy editing if needed
- File locking ensures thread-safe operations
- Default to enabled maintains existing bot behavior
- Toggle is instant - no confirmation required
- Status is shown in all PPCP sites menu views
