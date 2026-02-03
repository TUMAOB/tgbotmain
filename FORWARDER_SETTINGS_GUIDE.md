# Forwarder Settings Guide

## Overview
The forwarder settings feature allows admins and mods to configure multiple Telegram forwarders for both `/b3` and `/pp` commands. Each forwarder can have a custom name, bot token, and chat ID, and can be enabled/disabled independently.

## Features

### 1. **Multiple Forwarders per Gateway**
- Each gateway (`/b3` and `/pp`) can have multiple forwarders
- Each forwarder is independent and can be managed separately
- Forwarders can be enabled or disabled without removing them

### 2. **Custom Configuration**
- **Name**: Custom name for easy identification (e.g., "Main Channel", "Backup Channel")
- **Bot Token**: Telegram bot token for sending messages
- **Chat ID**: Target chat/channel ID where messages will be forwarded
- **Enabled/Disabled**: Toggle to enable or disable forwarding without deleting the configuration

### 3. **Test Functionality**
- Each forwarder has a test button
- Sends a test message to verify the configuration
- Shows success or error message immediately

## How to Access

1. Open the admin menu: `/admin`
2. Click on **⚙️ Settings**
3. Choose either:
   - **📡 B3 Forwarders** - for `/b3` command forwarders
   - **📡 PP Forwarders** - for `/pp` command forwarders

## Managing Forwarders

### Adding a Forwarder

1. Click **➕ Add Forwarder**
2. Enter a custom name (e.g., "My Channel")
3. Enter the bot token (e.g., `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Enter the chat ID (e.g., `-1001234567890` or `@channelname`)
5. The forwarder will be created and enabled automatically

### Viewing Forwarder Details

1. Click on the forwarder name in the list
2. View the configuration:
   - Name
   - Bot Token (masked for security)
   - Chat ID
   - Status (Enabled/Disabled)

### Editing a Forwarder

From the forwarder details view, you can:
- **✏️ Edit Name**: Change the forwarder name
- **🔑 Edit Token**: Update the bot token
- **💬 Edit Chat ID**: Change the target chat/channel

### Enabling/Disabling a Forwarder

1. Open the forwarder details
2. Click **🔴 Disable** or **🟢 Enable**
3. The status will toggle immediately

### Testing a Forwarder

1. Click **🧪 Test** next to the forwarder name (or in the details view)
2. A test message will be sent to the configured chat
3. You'll see a success or error notification

### Removing a Forwarder

1. Open the forwarder details
2. Click **🗑️ Remove**
3. The forwarder will be deleted permanently

## How It Works

### Forwarding Logic

When a card is checked using `/b3` or `/pp` and the result is approved:
1. The result is sent to the default channel (if configured via `FORWARD_CHANNEL_ID`)
2. The result is sent to all **enabled** forwarders for that gateway
3. Each forwarder uses its own bot token and chat ID
4. Errors are logged but don't stop other forwarders from working

### Approved Card Detection

A card is considered approved if the result contains:
- For `/b3`: "APPROVED" and "✅"
- For `/pp`: "CCN" or "CVV" with "✅"

### Database Structure

Forwarders are stored in `forwarders_db.json`:

```json
{
  "b3": [
    {
      "name": "Main B3 Channel",
      "bot_token": "1234567890:ABCdefGHI",
      "chat_id": "-1001234567890",
      "enabled": true
    },
    {
      "name": "Backup B3 Channel",
      "bot_token": "9876543210:XYZabcDEF",
      "chat_id": "-1009876543210",
      "enabled": false
    }
  ],
  "pp": [
    {
      "name": "PP Channel",
      "bot_token": "1111111111:AAAAA",
      "chat_id": "-1001111111111",
      "enabled": true
    }
  ]
}
```

## Security Considerations

1. **Bot Token Masking**: Bot tokens are masked in the UI (showing only first 10 and last 5 characters)
2. **Admin/Mod Only**: Only admins and mods can access forwarder settings
3. **File Locking**: Database operations use file locking to prevent race conditions
4. **Error Handling**: Errors in one forwarder don't affect others

## Troubleshooting

### Test Message Fails

**Possible causes:**
1. Invalid bot token
2. Bot is not a member of the target chat/channel
3. Bot doesn't have permission to send messages
4. Invalid chat ID format

**Solutions:**
1. Verify the bot token is correct
2. Add the bot to the target chat/channel
3. Grant the bot admin permissions (for channels)
4. Check the chat ID format (should start with `-` for groups/channels)

### Forwarder Not Sending Messages

**Check:**
1. Is the forwarder enabled? (🟢 status)
2. Is the card result approved? (contains "✅")
3. Check the bot logs for error messages
4. Test the forwarder using the test button

### Multiple Forwarders Not Working

**Verify:**
1. Each forwarder has a unique bot token
2. Each bot is properly configured in Telegram
3. Network connectivity is working
4. No rate limiting from Telegram API

## API Reference

### Functions

#### `load_forwarders_db()`
Load forwarders database from file.

**Returns:** `dict` - Database structure with 'b3' and 'pp' keys

#### `save_forwarders_db(db)`
Save forwarders database to file.

**Parameters:**
- `db` (dict): Database structure to save

#### `add_forwarder(gateway, name, bot_token, chat_id)`
Add a new forwarder.

**Parameters:**
- `gateway` (str): 'b3' or 'pp'
- `name` (str): Custom name for the forwarder
- `bot_token` (str): Telegram bot token
- `chat_id` (str): Target chat/channel ID

**Returns:** `bool` - True if successful

#### `remove_forwarder(gateway, index)`
Remove a forwarder by index.

**Parameters:**
- `gateway` (str): 'b3' or 'pp'
- `index` (int): Index of the forwarder to remove

**Returns:** `bool` - True if successful, False if index is invalid

#### `update_forwarder(gateway, index, name=None, bot_token=None, chat_id=None, enabled=None)`
Update a forwarder.

**Parameters:**
- `gateway` (str): 'b3' or 'pp'
- `index` (int): Index of the forwarder to update
- `name` (str, optional): New name
- `bot_token` (str, optional): New bot token
- `chat_id` (str, optional): New chat ID
- `enabled` (bool, optional): New enabled status

**Returns:** `bool` - True if successful, False if index is invalid

#### `get_forwarders(gateway)`
Get all forwarders for a gateway.

**Parameters:**
- `gateway` (str): 'b3' or 'pp'

**Returns:** `list` - List of forwarder dictionaries

## Examples

### Example 1: Adding a B3 Forwarder via Admin Menu

1. `/admin` → **⚙️ Settings** → **📡 B3 Forwarders**
2. Click **➕ Add Forwarder**
3. Enter name: `Main Channel`
4. Enter token: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
5. Enter chat ID: `-1001234567890`
6. Done! The forwarder is now active

### Example 2: Testing a Forwarder

1. `/admin` → **⚙️ Settings** → **📡 PP Forwarders**
2. Click **🧪 Test** next to the forwarder
3. Check the target channel for the test message
4. If successful, you'll see: "✅ Test message sent successfully to [name]!"

### Example 3: Disabling a Forwarder Temporarily

1. `/admin` → **⚙️ Settings** → **📡 B3 Forwarders**
2. Click on the forwarder name
3. Click **🔴 Disable**
4. The forwarder will stop sending messages but configuration is preserved
5. Re-enable anytime with **🟢 Enable**

## Best Practices

1. **Use Descriptive Names**: Name forwarders clearly (e.g., "Main Channel", "Backup Channel", "Test Channel")
2. **Test Before Use**: Always test a forwarder after adding or editing
3. **Keep Backups**: Maintain at least one backup forwarder in case the primary fails
4. **Monitor Logs**: Check bot logs regularly for forwarding errors
5. **Disable Unused**: Disable forwarders you're not using instead of deleting them
6. **Secure Tokens**: Never share bot tokens publicly

## Changelog

### Version 1.0 (Initial Release)
- Added forwarder management for B3 and PP gateways
- Support for multiple forwarders per gateway
- Add, edit, remove, enable/disable functionality
- Test button for each forwarder
- Integration with existing `/b3` and `/pp` commands
- Secure bot token masking in UI
- File-based database with locking for thread safety
