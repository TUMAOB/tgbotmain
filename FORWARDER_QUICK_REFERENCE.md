# Forwarder Settings - Quick Reference

## Access Path
```
/admin → ⚙️ Settings → 📡 B3/PP Forwarders
```

## Quick Actions

### Add Forwarder
1. Click **➕ Add Forwarder**
2. Enter: Name → Token → Chat ID
3. Done! (Auto-enabled)

### Test Forwarder
- Click **🧪 Test** next to forwarder name
- Check target channel for test message

### Enable/Disable
- Click forwarder name → **🔴 Disable** / **🟢 Enable**

### Edit
- Click forwarder name → **✏️ Edit** (Name/Token/Chat)

### Remove
- Click forwarder name → **🗑️ Remove**

## Forwarder Status Icons
- 🟢 = Enabled (actively forwarding)
- 🔴 = Disabled (not forwarding)

## When Forwarding Happens

### /b3 Command
- Triggers when result contains: `APPROVED` + `✅`
- Forwards to all enabled B3 forwarders

### /pp Command
- Triggers when result contains: `CCN`/`CVV` + `✅`
- Forwards to all enabled PP forwarders

## Database Location
```
/vercel/sandbox/forwarders_db.json
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Test fails | Check bot token, chat ID, and bot permissions |
| Not forwarding | Verify forwarder is enabled (🟢) |
| Multiple errors | Test each forwarder individually |
| Token invalid | Edit token and test again |

## Example Configuration

### B3 Forwarder
```
Name: Main B3 Channel
Token: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
Chat ID: -1001234567890
Status: 🟢 Enabled
```

### PP Forwarder
```
Name: PP Results Channel
Token: 9876543210:XYZabcDEFghiJKLmnoPQRstuVWX
Chat ID: @myppresults
Status: 🟢 Enabled
```

## Tips
- ✅ Use descriptive names
- ✅ Test after adding/editing
- ✅ Keep at least one backup forwarder
- ✅ Disable instead of delete (preserves config)
- ✅ Monitor bot logs for errors

## Keyboard Shortcuts (in menu)
- **➕** = Add new
- **🧪** = Test
- **✏️** = Edit
- **🔴/🟢** = Toggle enable/disable
- **🗑️** = Remove
- **⬅️** = Go back
