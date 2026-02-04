"""
System Manager Module
Handles backup, restore, and system update functionality for the Telegram bot.
"""

import os
import json
import shutil
import zipfile
import tempfile
import requests
import glob
from datetime import datetime
from typing import Tuple, List, Optional, Dict
from filelock import SoftFileLock

# Backup directory
BACKUP_DIR = 'backups'
BACKUP_DIR_LOCK = 'backups.lock'

# Files and directories to backup
DATABASE_FILES = [
    'users_db.json',
    'mods_db.json',
    'forwarders_db.json',
    'bot_settings.json',
    'mass_settings.json',
    'gateway_interval_settings.json',
    'auto_scan_settings.json',
    'ppcp_auto_remove_settings.json',
    'site_freeze_state.json',
]

# Gateway site files
GATEWAY_SITES = [
    'ppcp/sites.txt',
    'paypalpro/sites.txt',
]

# Bot token file
BOT_TOKEN_FILE = 'bot_token.txt'

# Core system files that will be updated
SYSTEM_FILES = [
    'auth.py',
    'run_production.py',
    'requirements.txt',
    'system_manager.py',
]

# Core module directories
CORE_MODULES = [
    'core',
    'ppcp',
    'paypalpro',
]


def ensure_backup_dir():
    """Ensure backup directory exists"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)


def get_backup_list() -> List[Dict]:
    """Get list of available backups"""
    ensure_backup_dir()
    backups = []
    
    for item in os.listdir(BACKUP_DIR):
        backup_path = os.path.join(BACKUP_DIR, item)
        if os.path.isdir(backup_path):
            # Check if it's a valid backup directory
            metadata_file = os.path.join(backup_path, 'backup_metadata.json')
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        metadata['name'] = item
                        metadata['path'] = backup_path
                        backups.append(metadata)
                except:
                    # If metadata is corrupted, still list it
                    backups.append({
                        'name': item,
                        'path': backup_path,
                        'created_at': 'Unknown',
                        'type': 'Unknown'
                    })
    
    # Sort by creation date (newest first)
    backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return backups


def create_backup(backup_type: str = 'full', description: str = '') -> Tuple[bool, str, str]:
    """
    Create a backup of the system.
    
    Args:
        backup_type: 'full' (all data), 'databases' (only databases), 'sites' (only site folders)
        description: Optional description for the backup
        
    Returns:
        Tuple of (success, message, backup_name)
    """
    ensure_backup_dir()
    
    # Create backup folder with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'backup_{backup_type}_{timestamp}'
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    try:
        os.makedirs(backup_path)
        
        backed_up_items = []
        
        # Backup database files
        if backup_type in ['full', 'databases']:
            db_backup_path = os.path.join(backup_path, 'databases')
            os.makedirs(db_backup_path, exist_ok=True)
            
            for db_file in DATABASE_FILES:
                if os.path.exists(db_file):
                    shutil.copy2(db_file, os.path.join(db_backup_path, os.path.basename(db_file)))
                    backed_up_items.append(db_file)
        
        # Backup gateway sites
        if backup_type in ['full', 'databases', 'sites']:
            sites_backup_path = os.path.join(backup_path, 'gateway_sites')
            os.makedirs(sites_backup_path, exist_ok=True)
            
            for site_file in GATEWAY_SITES:
                if os.path.exists(site_file):
                    # Create subdirectory structure
                    site_dir = os.path.dirname(site_file)
                    target_dir = os.path.join(sites_backup_path, site_dir)
                    os.makedirs(target_dir, exist_ok=True)
                    shutil.copy2(site_file, os.path.join(target_dir, os.path.basename(site_file)))
                    backed_up_items.append(site_file)
        
        # Backup bot token
        if backup_type in ['full', 'databases']:
            if os.path.exists(BOT_TOKEN_FILE):
                shutil.copy2(BOT_TOKEN_FILE, os.path.join(backup_path, BOT_TOKEN_FILE))
                backed_up_items.append(BOT_TOKEN_FILE)
        
        # Backup B3 site folders (site_* directories)
        if backup_type in ['full', 'sites']:
            b3_sites_backup_path = os.path.join(backup_path, 'b3_sites')
            os.makedirs(b3_sites_backup_path, exist_ok=True)
            
            for item in os.listdir('.'):
                if os.path.isdir(item) and (item.startswith('site_') or item.startswith('site')):
                    # Check if it's a valid site folder
                    site_txt = os.path.join(item, 'site.txt')
                    if os.path.exists(site_txt):
                        # Copy entire site folder
                        target_path = os.path.join(b3_sites_backup_path, item)
                        shutil.copytree(item, target_path)
                        backed_up_items.append(f'{item}/')
        
        # Backup forwarders database
        if backup_type in ['full', 'databases']:
            forwarders_file = 'forwarders_db.json'
            if os.path.exists(forwarders_file):
                db_backup_path = os.path.join(backup_path, 'databases')
                os.makedirs(db_backup_path, exist_ok=True)
                shutil.copy2(forwarders_file, os.path.join(db_backup_path, forwarders_file))
                if forwarders_file not in backed_up_items:
                    backed_up_items.append(forwarders_file)
        
        # Create metadata file
        metadata = {
            'created_at': datetime.now().isoformat(),
            'type': backup_type,
            'description': description,
            'items': backed_up_items,
            'item_count': len(backed_up_items)
        }
        
        with open(os.path.join(backup_path, 'backup_metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return True, f"Backup created successfully with {len(backed_up_items)} items", backup_name
        
    except Exception as e:
        # Clean up on failure
        if os.path.exists(backup_path):
            shutil.rmtree(backup_path)
        return False, f"Backup failed: {str(e)}", ''


def restore_backup(backup_name: str, restore_type: str = 'full') -> Tuple[bool, str]:
    """
    Restore from a backup.
    
    Args:
        backup_name: Name of the backup to restore
        restore_type: 'full' (all data), 'databases' (only databases), 'sites' (only site folders)
        
    Returns:
        Tuple of (success, message)
    """
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    if not os.path.exists(backup_path):
        return False, f"Backup '{backup_name}' not found"
    
    try:
        restored_items = []
        
        # Restore database files
        if restore_type in ['full', 'databases']:
            db_backup_path = os.path.join(backup_path, 'databases')
            if os.path.exists(db_backup_path):
                for db_file in os.listdir(db_backup_path):
                    src = os.path.join(db_backup_path, db_file)
                    dst = db_file
                    shutil.copy2(src, dst)
                    restored_items.append(db_file)
        
        # Restore gateway sites
        if restore_type in ['full', 'databases', 'sites']:
            sites_backup_path = os.path.join(backup_path, 'gateway_sites')
            if os.path.exists(sites_backup_path):
                for root, dirs, files in os.walk(sites_backup_path):
                    for file in files:
                        src = os.path.join(root, file)
                        # Calculate relative path from sites_backup_path
                        rel_path = os.path.relpath(src, sites_backup_path)
                        dst = rel_path
                        # Ensure directory exists
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        restored_items.append(rel_path)
        
        # Restore bot token
        if restore_type in ['full', 'databases']:
            token_backup = os.path.join(backup_path, BOT_TOKEN_FILE)
            if os.path.exists(token_backup):
                shutil.copy2(token_backup, BOT_TOKEN_FILE)
                restored_items.append(BOT_TOKEN_FILE)
        
        # Restore B3 site folders
        if restore_type in ['full', 'sites']:
            b3_sites_backup_path = os.path.join(backup_path, 'b3_sites')
            if os.path.exists(b3_sites_backup_path):
                for site_folder in os.listdir(b3_sites_backup_path):
                    src = os.path.join(b3_sites_backup_path, site_folder)
                    dst = site_folder
                    
                    # Remove existing folder if it exists
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    
                    # Copy the backup
                    shutil.copytree(src, dst)
                    restored_items.append(f'{site_folder}/')
        
        return True, f"Restored {len(restored_items)} items successfully"
        
    except Exception as e:
        return False, f"Restore failed: {str(e)}"


def delete_backup(backup_name: str) -> Tuple[bool, str]:
    """Delete a backup"""
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    if not os.path.exists(backup_path):
        return False, f"Backup '{backup_name}' not found"
    
    try:
        shutil.rmtree(backup_path)
        return True, f"Backup '{backup_name}' deleted successfully"
    except Exception as e:
        return False, f"Failed to delete backup: {str(e)}"


def download_github_repo(repo_url: str) -> Tuple[bool, str, str]:
    """
    Download a GitHub repository as a ZIP file.
    
    Args:
        repo_url: GitHub repository URL (e.g., https://github.com/user/repo)
        
    Returns:
        Tuple of (success, message, temp_dir_path)
    """
    try:
        # Parse GitHub URL to get the ZIP download URL
        # Support formats:
        # - https://github.com/user/repo
        # - https://github.com/user/repo.git
        # - https://github.com/user/repo/tree/branch
        
        repo_url = repo_url.strip()
        
        # Remove .git suffix if present
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]
        
        # Extract branch if specified
        branch = 'main'
        if '/tree/' in repo_url:
            parts = repo_url.split('/tree/')
            repo_url = parts[0]
            branch = parts[1].split('/')[0]
        
        # Construct ZIP download URL
        zip_url = f"{repo_url}/archive/refs/heads/{branch}.zip"
        
        # Try main branch first, then master
        response = requests.get(zip_url, timeout=60, stream=True)
        
        if response.status_code == 404:
            # Try master branch
            branch = 'master'
            zip_url = f"{repo_url}/archive/refs/heads/{branch}.zip"
            response = requests.get(zip_url, timeout=60, stream=True)
        
        if response.status_code != 200:
            return False, f"Failed to download repository: HTTP {response.status_code}", ''
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix='github_update_')
        zip_path = os.path.join(temp_dir, 'repo.zip')
        
        # Save ZIP file
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Extract ZIP
        extract_dir = os.path.join(temp_dir, 'extracted')
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Find the extracted folder (usually repo-branch)
        extracted_items = os.listdir(extract_dir)
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
            source_dir = os.path.join(extract_dir, extracted_items[0])
        else:
            source_dir = extract_dir
        
        return True, f"Repository downloaded successfully (branch: {branch})", source_dir
        
    except requests.exceptions.Timeout:
        return False, "Download timed out. Please try again.", ''
    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}", ''
    except Exception as e:
        return False, f"Error downloading repository: {str(e)}", ''


def extract_zip_file(zip_path: str) -> Tuple[bool, str, str]:
    """
    Extract a ZIP file to a temporary directory.
    
    Args:
        zip_path: Path to the ZIP file
        
    Returns:
        Tuple of (success, message, temp_dir_path)
    """
    try:
        if not os.path.exists(zip_path):
            return False, f"ZIP file not found: {zip_path}", ''
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix='zip_update_')
        extract_dir = os.path.join(temp_dir, 'extracted')
        
        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Find the source directory
        extracted_items = os.listdir(extract_dir)
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
            source_dir = os.path.join(extract_dir, extracted_items[0])
        else:
            source_dir = extract_dir
        
        return True, "ZIP file extracted successfully", source_dir
        
    except zipfile.BadZipFile:
        return False, "Invalid ZIP file", ''
    except Exception as e:
        return False, f"Error extracting ZIP: {str(e)}", ''


def apply_system_update(source_dir: str, create_backup: bool = True) -> Tuple[bool, str, List[str]]:
    """
    Apply a system update from a source directory.
    
    Args:
        source_dir: Path to the directory containing the update files
        create_backup: Whether to create a backup before updating
        
    Returns:
        Tuple of (success, message, list of updated files)
    """
    updated_files = []
    
    try:
        # Create backup before updating
        if create_backup:
            backup_success, backup_msg, backup_name = create_backup_func('full', 'Pre-update backup')
            if not backup_success:
                return False, f"Failed to create backup: {backup_msg}", []
        
        # Update system files
        for sys_file in SYSTEM_FILES:
            src = os.path.join(source_dir, sys_file)
            if os.path.exists(src):
                shutil.copy2(src, sys_file)
                updated_files.append(sys_file)
        
        # Update core modules
        for module_dir in CORE_MODULES:
            src_dir = os.path.join(source_dir, module_dir)
            if os.path.exists(src_dir) and os.path.isdir(src_dir):
                # Remove existing module directory
                if os.path.exists(module_dir):
                    shutil.rmtree(module_dir)
                # Copy new module directory
                shutil.copytree(src_dir, module_dir)
                updated_files.append(f'{module_dir}/')
        
        # Check for any additional Python files in root
        for item in os.listdir(source_dir):
            if item.endswith('.py') and item not in SYSTEM_FILES:
                src = os.path.join(source_dir, item)
                if os.path.isfile(src):
                    shutil.copy2(src, item)
                    updated_files.append(item)
        
        # Update requirements.txt if present
        req_src = os.path.join(source_dir, 'requirements.txt')
        if os.path.exists(req_src):
            shutil.copy2(req_src, 'requirements.txt')
            if 'requirements.txt' not in updated_files:
                updated_files.append('requirements.txt')
        
        return True, f"System updated successfully. {len(updated_files)} files updated.", updated_files
        
    except Exception as e:
        return False, f"Update failed: {str(e)}", updated_files


def get_backup_info(backup_name: str) -> Optional[Dict]:
    """Get detailed information about a backup"""
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    if not os.path.exists(backup_path):
        return None
    
    metadata_file = os.path.join(backup_path, 'backup_metadata.json')
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                metadata['name'] = backup_name
                metadata['path'] = backup_path
                
                # Calculate backup size
                total_size = 0
                for root, dirs, files in os.walk(backup_path):
                    for file in files:
                        total_size += os.path.getsize(os.path.join(root, file))
                metadata['size_bytes'] = total_size
                metadata['size_mb'] = round(total_size / (1024 * 1024), 2)
                
                return metadata
        except:
            pass
    
    return {
        'name': backup_name,
        'path': backup_path,
        'created_at': 'Unknown',
        'type': 'Unknown'
    }


def cleanup_temp_dir(temp_dir: str):
    """Clean up a temporary directory"""
    try:
        if temp_dir and os.path.exists(temp_dir):
            # Find the parent temp directory
            parent = os.path.dirname(temp_dir)
            if 'github_update_' in parent or 'zip_update_' in parent:
                shutil.rmtree(parent)
            elif 'github_update_' in temp_dir or 'zip_update_' in temp_dir:
                shutil.rmtree(temp_dir)
    except:
        pass


def get_system_info() -> Dict:
    """Get current system information"""
    info = {
        'database_files': [],
        'gateway_sites': [],
        'b3_sites': [],
        'core_modules': [],
        'backup_count': 0,
    }
    
    # Check database files
    for db_file in DATABASE_FILES:
        if os.path.exists(db_file):
            info['database_files'].append({
                'name': db_file,
                'size': os.path.getsize(db_file)
            })
    
    # Check gateway sites
    for site_file in GATEWAY_SITES:
        if os.path.exists(site_file):
            with open(site_file, 'r') as f:
                lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
            info['gateway_sites'].append({
                'name': site_file,
                'count': len(lines)
            })
    
    # Check B3 sites
    for item in os.listdir('.'):
        if os.path.isdir(item) and (item.startswith('site_') or item.startswith('site')):
            site_txt = os.path.join(item, 'site.txt')
            if os.path.exists(site_txt):
                info['b3_sites'].append(item)
    
    # Check core modules
    for module in CORE_MODULES:
        if os.path.exists(module) and os.path.isdir(module):
            info['core_modules'].append(module)
    
    # Count backups
    ensure_backup_dir()
    info['backup_count'] = len([d for d in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, d))])
    
    return info


# Alias for create_backup to avoid naming conflict
create_backup_func = create_backup
