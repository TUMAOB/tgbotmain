# PPCP Auto-Remove Quick Guide

## What Was Added
A toggle switch in the admin PPCP settings to control automatic removal of bad sites.

## How to Use

### Access the Toggle
1. Send `/admin` to the bot
2. Click **⚙️ Settings**
3. Click **🔗 PPCP Sites**
4. Click **🗑️ Auto-Remove Bad Sites: 🟢 ON** to toggle

### Toggle States
- **🟢 ON** (Default): Bad sites are automatically removed from the pool
- **🔴 OFF**: Bad sites are NOT removed, admin must manually remove them

## When to Use

### Keep ON (🟢) When:
- Running production checks
- Want automatic cleanup of non-working sites
- Normal operation

### Turn OFF (🔴) When:
- Testing new sites
- Troubleshooting site issues
- Want to manually review bad sites before removal
- Debugging PPCP checker behavior

## Technical Details
- **Settings File**: `ppcp_auto_remove_settings.json`
- **Default**: Enabled (ON)
- **Scope**: Affects all PPCP site checks
- **Persistence**: Setting is saved and persists across bot restarts

## What Happens When OFF
When auto-remove is disabled:
1. PPCP checker still detects bad sites
2. Bad sites are logged but NOT removed
3. Sites remain in `ppcp/sites.txt`
4. Sites continue to be used in rotation
5. Admin must manually remove bad sites via the menu

## Example Use Case
```
Scenario: Testing a new PPCP site that might have temporary issues

1. Turn auto-remove OFF (🔴)
2. Add the new site
3. Run checks - if site fails, it won't be auto-removed
4. Fix the site issues
5. Test again
6. Once stable, turn auto-remove back ON (🟢)
```

## Files Modified
- `auth.py` - Added toggle UI and settings management
- `ppcp/site_manager.py` - Added auto-remove check before removal

## Backward Compatibility
✓ Existing behavior preserved (defaults to ON)
✓ No changes needed to existing code
✓ Works with all existing PPCP functionality
