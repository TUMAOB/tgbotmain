# System Management Guide

## Overview

The `/system` command provides admin-only access to system management features including:
- **Backup**: Create backups of databases, sites, and configurations
- **Restore**: Restore from previous backups
- **Update**: Update the bot system from GitHub or ZIP files

## Command

```
/system
```

**Access**: Admin only (ADMIN_ID)

## Features

### 💾 Create Backup

Create backups of your bot data with three options:

1. **Full Backup**: Everything including:
   - All database files (users_db.json, mods_db.json, forwarders_db.json, etc.)
   - Gateway sites (ppcp/sites.txt, paypalpro/sites.txt)
   - Bot token (bot_token.txt)
   - All B3 site folders (site_*, site_1, site_2, etc.)

2. **Databases Only**: 
   - All JSON database files
   - Bot settings
   - Bot token

3. **Sites Only**:
   - Gateway site configurations
   - B3 site folders

Backups are stored in the `backups/` directory with timestamps.

### 📂 View Backups

Browse all available backups with details:
- Creation date
- Backup type
- Number of items
- Size in MB
- List of backed up files

### ♻️ Restore Backup

Restore from any available backup with options:
- **Full Restore**: Restore everything
- **Databases Only**: Restore only database files
- **Sites Only**: Restore only site configurations

⚠️ **Warning**: Restoring will overwrite current data!

### 🔄 Update System

Update the bot from external sources:

#### From GitHub URL
1. Select "From GitHub URL"
2. Send the repository URL:
   - `https://github.com/user/repo`
   - `https://github.com/user/repo.git`
   - `https://github.com/user/repo/tree/branch`

The system will:
1. Download the repository
2. Create a backup automatically
3. Update system files (auth.py, core/, ppcp/, paypalpro/, etc.)

#### From ZIP File
1. Select "From ZIP File"
2. Send a ZIP file containing the update

The ZIP should contain the updated bot files in the root or a single subdirectory.

### 📊 System Info

View current system status:
- Database files and sizes
- Gateway sites count
- B3 sites list
- Core modules
- Total backups

## Files Backed Up

### Database Files
- `users_db.json` - User access database
- `mods_db.json` - Moderators database
- `forwarders_db.json` - Forwarder configurations
- `bot_settings.json` - Bot settings
- `mass_settings.json` - Mass check settings
- `gateway_interval_settings.json` - Gateway intervals
- `auto_scan_settings.json` - Auto-scan settings
- `ppcp_auto_remove_settings.json` - PPCP auto-remove settings
- `site_freeze_state.json` - Site freeze states

### Gateway Sites
- `ppcp/sites.txt` - PPCP gateway sites
- `paypalpro/sites.txt` - PayPal Pro gateway sites

### B3 Sites
All directories matching `site_*` or `site` pattern containing:
- `site.txt` - Site URL
- `cookies_*.txt` - Cookie files
- `proxy.txt` - Proxy configuration

### System Files (Updated)
- `auth.py` - Main bot file
- `run_production.py` - Production runner
- `requirements.txt` - Dependencies
- `system_manager.py` - System manager module
- `core/` - Core modules directory
- `ppcp/` - PPCP gateway module
- `paypalpro/` - PayPal Pro gateway module

## Backup Directory Structure

```
backups/
├── backup_full_20240115_143022/
│   ├── backup_metadata.json
│   ├── databases/
│   │   ├── users_db.json
│   │   ├── mods_db.json
│   │   └── ...
│   ├── gateway_sites/
│   │   ├── ppcp/sites.txt
│   │   └── paypalpro/sites.txt
│   ├── b3_sites/
│   │   ├── site_1/
│   │   └── site_2/
│   └── bot_token.txt
└── backup_databases_20240115_150000/
    ├── backup_metadata.json
    └── databases/
        └── ...
```

## Important Notes

1. **Restart Required**: After updating the system, you must restart the bot for changes to take effect.

2. **Automatic Backup**: When updating, a full backup is automatically created before applying changes.

3. **Admin Only**: All system management features are restricted to the admin user (ADMIN_ID).

4. **Data Safety**: Always verify backups are working before making major changes.

5. **GitHub Updates**: The system tries `main` branch first, then `master` if not found.

## Troubleshooting

### Update Failed
- Check the GitHub URL is correct and accessible
- Ensure the repository contains the expected file structure
- Check network connectivity

### Restore Failed
- Verify the backup exists and is not corrupted
- Check file permissions
- Ensure enough disk space

### Backup Failed
- Check disk space
- Verify write permissions to backups directory
- Check if files are locked by other processes
