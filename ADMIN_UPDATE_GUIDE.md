# Admin Guide: System Updates & Backups

## New Features

### 1. Progress Tracking During Updates
When you update the system (via GitHub or ZIP), you'll now see:
- **Real-time progress bar**: `███████░░░ 70%`
- **Current operation**: What's happening right now
- **File updates**: Which files are being updated

### 2. Automatic Restart Script
After every successful update, a restart script is automatically created:

**File**: `restart_bot.sh`

**Usage**:
```bash
bash restart_bot.sh
```

**What it does**:
1. Finds the running bot process
2. Stops it gracefully (waits up to 10 seconds)
3. Force kills if necessary
4. Starts the bot in background
5. Logs output to `bot.log`

**Manual restart** (if script fails):
```bash
python3 run_production.py
```

### 3. Backup Download as ZIP
You can now download any backup as a ZIP file directly in Telegram!

**Steps**:
1. `/system` → View Backups
2. Select a backup
3. Click "📥 Download ZIP"
4. ZIP file will be sent to the chat

**Benefits**:
- Easy to download and store offline
- Can restore on different server
- Compressed (smaller file size)
- Contains all backup data

## Quick Commands

### Update from GitHub
```
/system → Update System → From GitHub URL
Send: https://github.com/username/repo
```

**Progress shown**:
```
⏳ System Update in Progress

Progress: ███████░░░ 70%
Status: Updated: auth.py
```

**After completion**:
```
✅ System Updated Successfully
📦 Updated 15 files

🔄 Restart Options:
1. Run: `bash restart_bot.sh`
2. Or manually: `python3 run_production.py`
```

### Update from ZIP
```
/system → Update System → From ZIP File
Send: [your_update.zip]
```

Same progress tracking and restart instructions.

### Create Backup with ZIP
```
/system → Create Backup → [Full/Databases/Sites]
```

**Result**:
- Backup directory created in `backups/`
- ZIP file automatically created: `backups/backup_name.zip`
- Ready for download anytime

### Download Backup
```
/system → View Backups → [Select backup] → Download ZIP
```

**What you get**:
- ZIP file sent to Telegram chat
- File size shown before upload
- Can save to your device

## Restart Script Details

### What the script does:
```bash
#!/bin/bash
# Auto-generated restart script

# 1. Find bot process
BOT_PID=$(pgrep -f "python.*run_production.py")

# 2. Stop gracefully
kill $BOT_PID

# 3. Wait for shutdown (max 10 seconds)
# ... waiting ...

# 4. Force kill if needed
kill -9 $BOT_PID

# 5. Start bot in background
nohup python3 run_production.py > bot.log 2>&1 &
```

### View logs after restart:
```bash
tail -f bot.log
```

### Check if bot is running:
```bash
pgrep -f "python.*run_production.py"
```

### Stop bot manually:
```bash
kill $(pgrep -f "python.*run_production.py")
```

## Backup ZIP Contents

When you download a backup ZIP, it contains:

```
backup_full_20260204_143022.zip
├── backup_metadata.json      # Backup info
├── databases/
│   ├── users_db.json
│   ├── mods_db.json
│   ├── forwarders_db.json
│   ├── bot_settings.json
│   └── ...
├── gateway_sites/
│   ├── ppcp/sites.txt
│   └── paypalpro/sites.txt
├── b3_sites/
│   ├── site_1/
│   └── site_2/
└── bot_token.txt
```

## Troubleshooting

### Update shows no progress
- Check internet connection
- Verify GitHub URL is correct
- Try again (might be temporary network issue)

### Restart script doesn't work
**Solution**: Restart manually
```bash
# Stop bot
kill $(pgrep -f "python.*run_production.py")

# Wait 2 seconds
sleep 2

# Start bot
python3 run_production.py
```

### Backup ZIP download fails
**Possible causes**:
- File too large for Telegram (max 50MB)
- Network timeout

**Solution**: Access ZIP directly on server
```bash
ls -lh backups/*.zip
# Copy the ZIP file manually
```

### Bot doesn't restart after update
**Check if bot is running**:
```bash
pgrep -f "python.*run_production.py"
```

**If not running, start it**:
```bash
python3 run_production.py
```

**Check logs for errors**:
```bash
tail -50 bot.log
```

## Best Practices

### Before Updating
1. ✅ Create a backup first
2. ✅ Download the backup ZIP
3. ✅ Note current bot version/state
4. ✅ Ensure you have server access

### After Updating
1. ✅ Read the update summary
2. ✅ Use the restart script or restart manually
3. ✅ Check bot is running: `/start` command
4. ✅ Test critical features
5. ✅ Monitor logs for errors

### Backup Strategy
1. **Daily**: Create database backup
2. **Weekly**: Create full backup
3. **Before updates**: Always create full backup
4. **Download important backups**: Store offline

### Recovery Plan
If update fails:
1. Bot creates automatic pre-update backup
2. Use `/system` → Restore Backup
3. Select the pre-update backup
4. Restore full backup
5. Restart bot

## File Locations

```
/vercel/sandbox/
├── restart_bot.sh           # Auto-generated restart script
├── bot.log                  # Bot output logs
├── backups/
│   ├── backup_full_*/       # Backup directories
│   └── backup_full_*.zip    # Backup ZIP files
├── auth.py                  # Main bot file
├── system_manager.py        # System management
└── run_production.py        # Production runner
```

## Support

If you encounter issues:
1. Check this guide first
2. Review error messages carefully
3. Check `bot.log` for details
4. Restore from backup if needed
5. Contact developer with error logs

## Summary

**New capabilities**:
- ✅ Real-time update progress
- ✅ Automatic restart script generation
- ✅ Download backups as ZIP files
- ✅ Better error handling
- ✅ Clear instructions after updates

**Your workflow**:
1. Create backup → Download ZIP
2. Update system → Watch progress
3. Restart bot → Use provided script
4. Verify → Test bot functionality

**Safety**:
- Automatic pre-update backups
- Easy restore from ZIP files
- Clear error messages
- Graceful shutdown handling
