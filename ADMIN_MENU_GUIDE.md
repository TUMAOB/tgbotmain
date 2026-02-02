# Admin Menu Implementation Guide

## Overview
This document describes the new admin menu and site randomization features added to the card checker bot.

## Changes Made

### 1. Site Randomization ✅
**Problem:** Sites in `sites.txt` were being selected randomly but the list itself was not shuffled, leading to potential patterns.

**Solution:** Added `random.shuffle(sites)` to randomize the sites list when loaded.

**Files Modified:**
- `ppcp/async_ppcpgatewaycvv.py` - Line ~1050 (in `main_async()`)
- `ppcp/ppcpgatewaycvv.py` - Lines ~40 (in `check_single_card()`) and ~1120 (in `main()`)

**Code Added:**
```python
# Randomize sites list for better distribution
random.shuffle(sites)
```

### 2. Admin Menu System ✅
**New Feature:** Complete admin control panel for managing users and bot settings.

**Files Modified:**
- `auth.py` - Added admin menu commands and handlers

## Admin Commands

### `/admin` - Admin Control Panel
Opens an interactive menu with the following options:

#### 👥 Approve User
- Redirects to use `/approve <user_id>` command
- Allows setting access duration (1 day, 1 week, 1 month, lifetime)

#### 📋 List Users
- Shows all approved users
- Displays access status (Active/Expired/Lifetime)
- Shows days remaining for time-limited access

#### ⏱️ Set Check Interval
- Adjust the rate limit between card checks
- Options: 0.5s, 1s, 2s, 5s, 10s
- Applies to all future checks (non-admin users)
- Current default: 1 second

#### 📊 View Stats
- Total users count
- Active users count
- Expired users count
- Current check interval

#### 🗑️ Remove User
- Redirects to use `/remove <user_id>` command
- Removes user from approved list

#### ❌ Close
- Closes the admin menu

### `/approve <user_id>` - Quick Approve
Direct command to approve a user with duration selection.

**Example:**
```
/approve 7405189284
```

### `/remove <user_id>` - Remove User
Direct command to remove a user from the approved list.

**Example:**
```
/remove 7405189284
```

## Technical Implementation

### New Functions Added

1. **`admin_menu_command()`**
   - Displays the main admin control panel
   - Creates interactive keyboard with admin options

2. **`admin_callback_handler()`**
   - Handles all admin menu button clicks
   - Routes to appropriate actions

3. **`interval_callback_handler()`**
   - Handles check interval selection
   - Updates global `RATE_LIMIT_SECONDS` variable

4. **`remove_user_command()`**
   - Removes users from the database
   - Validates user ID before removal

### Callback Patterns

- `admin_*` - Admin menu actions
- `interval_*` - Check interval selection
- `duration_*` - User approval duration (existing)

## Usage Examples

### For Admins

1. **Open Admin Panel:**
   ```
   /admin
   ```

2. **Approve a New User:**
   ```
   /approve 1234567890
   ```
   Then select duration from the menu.

3. **Change Check Interval:**
   - Use `/admin` → "Set Check Interval"
   - Select desired interval (e.g., 2s)

4. **View User List:**
   - Use `/admin` → "List Users"
   - See all users and their status

5. **Remove a User:**
   ```
   /remove 1234567890
   ```

### For Regular Users

No changes to user experience. They continue using:
- `/b3 <card>` - Single card check (Braintree)
- `/b3s <cards>` - Mass check (Braintree)
- `/pp <card/cards>` - PPCP gateway check

## Rate Limiting

The check interval can now be adjusted by admins:
- **Default:** 1 second between checks
- **Adjustable:** 0.5s to 10s
- **Applies to:** Non-admin users only
- **Admin users:** No rate limiting

## Database Structure

User database (`users_db.json`) stores:
```json
{
  "user_id": {
    "user_id": 1234567890,
    "approved_date": "2026-02-02T10:30:00",
    "expiry_date": "2026-03-02T10:30:00",
    "access_type": "1month"
  }
}
```

Access types:
- `1day` - 24 hours access
- `1week` - 7 days access
- `1month` - 30 days access
- `lifetime` - Permanent access

## Security Features

1. **Admin-Only Access:** All admin commands check `user_id == ADMIN_ID`
2. **Thread-Safe:** Uses locks for database operations
3. **Validation:** User IDs validated before operations
4. **Expiry Checking:** Automatic expiry validation on each check

## Testing

All files compiled successfully without syntax errors:
```bash
python3 -m py_compile auth.py ppcp/async_ppcpgatewaycvv.py ppcp/ppcpgatewaycvv.py
```

## Future Enhancements

Potential improvements:
1. User statistics (cards checked, success rate)
2. Bulk user approval from file
3. Custom expiry dates
4. User activity logs
5. Notification system for expiring access
6. Per-user rate limits

## Support

For issues or questions, contact @TUMAOB
