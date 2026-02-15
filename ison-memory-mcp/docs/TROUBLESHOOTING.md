# ISON Memory MCP - Troubleshooting Guide

Solutions for common issues and problems with ISON Memory MCP.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Server Issues](#server-issues)
- [Database Issues](#database-issues)
- [Search Issues](#search-issues)
- [Memory Issues](#memory-issues)
- [Platform-Specific Issues](#platform-specific-issues)
- [Performance Issues](#performance-issues)
- [Debug Mode](#debug-mode)
- [Getting Help](#getting-help)

---

## Quick Diagnostics

### Health Check Commands

```bash
# Check installation
ison-memory --version

# View current configuration
ison-memory config

# Check memory statistics
ison-memory stats

# Test server startup
ison-memory serve --log-level debug
```

### Common Status Codes

| Exit Code | Meaning | Action |
|-----------|---------|--------|
| 0 | Success | - |
| 1 | General error | Check error message |
| 2 | Configuration error | Verify config file |
| 3 | Database error | Check database path/permissions |
| 4 | Connection error | Check network/ports |

---

## Installation Issues

### Issue: `command not found: ison-memory`

**Symptoms:**
```bash
$ ison-memory --version
bash: ison-memory: command not found
```

**Solutions:**

1. **Verify installation:**
   ```bash
   pip show ison-memory-mcp
   ```

2. **Check PATH includes pip scripts:**
   ```bash
   # Unix/Linux/macOS
   echo $PATH | grep -E "(\.local/bin|site-packages)"

   # Windows PowerShell
   $env:PATH -split ';' | Where-Object { $_ -match 'Scripts' }
   ```

3. **Reinstall with user flag:**
   ```bash
   pip install --user ison-memory-mcp

   # Add to PATH (Unix)
   export PATH="$HOME/.local/bin:$PATH"

   # Add to PATH (Windows PowerShell)
   $env:PATH += ";$env:APPDATA\Python\Python310\Scripts"
   ```

4. **Use full path:**
   ```bash
   python -m ison_memory_mcp.cli --version
   ```

### Issue: `ModuleNotFoundError: No module named 'ison_memory_mcp'`

**Symptoms:**
```
ModuleNotFoundError: No module named 'ison_memory_mcp'
```

**Solutions:**

1. **Install the package:**
   ```bash
   pip install ison-memory-mcp
   ```

2. **Check Python version (requires 3.10+):**
   ```bash
   python --version
   # Must be 3.10 or higher
   ```

3. **Install from source:**
   ```bash
   cd /path/to/ison-memory-mcp
   pip install -e .
   ```

### Issue: Dependency conflicts

**Symptoms:**
```
ERROR: Cannot install ison-memory-mcp because these package versions have conflicting dependencies.
```

**Solutions:**

1. **Create a fresh virtual environment:**
   ```bash
   python -m venv ison-memory-env
   source ison-memory-env/bin/activate  # Windows: ison-memory-env\Scripts\activate
   pip install ison-memory-mcp
   ```

2. **Update pip and try again:**
   ```bash
   pip install --upgrade pip
   pip install ison-memory-mcp
   ```

---

## Server Issues

### Issue: Server won't start

**Symptoms:**
```
Error: Failed to start server
Error: Address already in use
```

**Solutions:**

1. **Check if another instance is running:**
   ```bash
   # Unix/Linux/macOS
   ps aux | grep ison-memory
   pgrep -f ison-memory

   # Windows
   tasklist | findstr ison
   ```

2. **Kill existing processes:**
   ```bash
   # Unix/Linux/macOS
   pkill -f ison-memory

   # Windows
   taskkill /F /IM python.exe /FI "WINDOWTITLE eq ison-memory"
   ```

3. **Check port availability:**
   ```bash
   # For HTTP transport (if used)
   netstat -an | grep 3000
   ```

4. **Run with debug logging:**
   ```bash
   ison-memory serve --log-level debug
   ```

### Issue: Server crashes on startup

**Symptoms:**
```
Error: Database file is corrupted
Error: Cannot open database
```

**Solutions:**

1. **Check database file exists:**
   ```bash
   ls -la ~/.ison-memory/memory.db
   ```

2. **Verify file permissions:**
   ```bash
   # Unix/Linux/macOS
   chmod 600 ~/.ison-memory/memory.db

   # Check permissions
   ls -la ~/.ison-memory/
   ```

3. **Test database integrity:**
   ```bash
   sqlite3 ~/.ison-memory/memory.db "PRAGMA integrity_check;"
   ```

4. **Restore from backup:**
   ```bash
   ison-memory backups  # List available backups
   cp ~/.ison-memory/backups/backup_YYYYMMDD.db ~/.ison-memory/memory.db
   ```

5. **Start fresh (last resort):**
   ```bash
   mv ~/.ison-memory/memory.db ~/.ison-memory/memory.db.corrupt
   ison-memory serve  # Creates new database
   ```

### Issue: MCP connection timeout

**Symptoms:**
```
Error: Connection timeout
Error: Server not responding
```

**Solutions:**

1. **Increase timeout in client config:**
   ```json
   {
     "mcpServers": {
       "ison-memory": {
         "command": "ison-memory",
         "args": ["serve"],
         "timeout": 30000
       }
     }
   }
   ```

2. **Check server is running:**
   ```bash
   # Start manually and check output
   ison-memory serve --log-level debug
   ```

3. **Verify command path:**
   ```bash
   which ison-memory  # Unix
   where ison-memory  # Windows
   ```

---

## Database Issues

### Issue: "database is locked"

**Symptoms:**
```
sqlite3.OperationalError: database is locked
Error: Database lock timeout
```

**Solutions:**

1. **Close other connections:**
   ```bash
   # Find processes using the database
   fuser ~/.ison-memory/memory.db  # Linux
   lsof ~/.ison-memory/memory.db   # macOS
   ```

2. **Increase busy timeout:**
   ```toml
   # config.toml
   [storage]
   busy_timeout = 10000  # 10 seconds
   ```

3. **Remove stale lock files:**
   ```bash
   rm ~/.ison-memory/memory.db-wal
   rm ~/.ison-memory/memory.db-shm
   ```

4. **Switch to WAL mode (if not already):**
   ```toml
   [storage]
   wal_mode = true
   ```

### Issue: Database corruption

**Symptoms:**
```
Error: database disk image is malformed
sqlite3.DatabaseError: malformed database
```

**Solutions:**

1. **Check integrity:**
   ```bash
   sqlite3 ~/.ison-memory/memory.db "PRAGMA integrity_check;"
   ```

2. **Attempt recovery:**
   ```bash
   sqlite3 ~/.ison-memory/memory.db ".recover" | sqlite3 ~/.ison-memory/recovered.db
   ```

3. **Export and reimport:**
   ```bash
   # If server starts
   ison-memory export --format ison --output backup.ison

   # Move corrupt database
   mv ~/.ison-memory/memory.db ~/.ison-memory/memory.db.corrupt

   # Import from ISON backup
   # (Future: ison-memory import backup.ison)
   ```

4. **Restore from backup:**
   ```bash
   gunzip -c ~/.ison-memory/backups/backup_latest.db.gz > ~/.ison-memory/memory.db
   ```

### Issue: Database file too large

**Symptoms:**
- Slow queries
- High disk usage
- Long startup time

**Solutions:**

1. **Check current size:**
   ```bash
   ls -lh ~/.ison-memory/memory.db
   ison-memory stats
   ```

2. **Run compaction:**
   ```bash
   # Preview first
   ison-memory compact --strategy smart --dry-run

   # Execute
   ison-memory compact --strategy smart
   ```

3. **Vacuum database:**
   ```bash
   sqlite3 ~/.ison-memory/memory.db "VACUUM;"
   ```

4. **Adjust compaction settings:**
   ```toml
   [compaction]
   strategy = "aggressive"
   max_age_days = 30
   min_access_count = 3
   ```

---

## Search Issues

### Issue: Search returns no results

**Symptoms:**
- `search_memory` returns empty
- Known entities not found

**Solutions:**

1. **Check if data exists:**
   ```bash
   ison-memory stats
   # Should show entity/observation counts > 0
   ```

2. **Verify FTS index:**
   ```bash
   sqlite3 ~/.ison-memory/memory.db "SELECT count(*) FROM observations_fts;"
   ```

3. **Rebuild FTS index:**
   ```bash
   sqlite3 ~/.ison-memory/memory.db << EOF
   INSERT INTO observations_fts(observations_fts) VALUES('rebuild');
   EOF
   ```

4. **Try exact name search:**
   ```json
   {"query": "exact entity name"}
   ```

5. **Use wildcard search:**
   ```json
   {"query": "type*"}
   ```

### Issue: Search is slow

**Symptoms:**
- Search takes > 5 seconds
- Timeout on large queries

**Solutions:**

1. **Limit results:**
   ```json
   {"query": "search term", "maxResults": 10}
   ```

2. **Add entity type filter:**
   ```json
   {"query": "search term", "entityType": "person"}
   ```

3. **Check index health:**
   ```bash
   sqlite3 ~/.ison-memory/memory.db "PRAGMA integrity_check;"
   ```

4. **Optimize database:**
   ```bash
   sqlite3 ~/.ison-memory/memory.db "ANALYZE;"
   ```

---

## Memory Issues

### Issue: Memory not persisting

**Symptoms:**
- Created entities disappear
- Observations not saved
- Empty database after restart

**Solutions:**

1. **Verify database path:**
   ```bash
   ison-memory config | grep storage
   ```

2. **Check write permissions:**
   ```bash
   touch ~/.ison-memory/test.txt && rm ~/.ison-memory/test.txt
   ```

3. **Verify server is using correct database:**
   ```bash
   ISON_MEMORY_SERVER_LOG_LEVEL=debug ison-memory serve
   # Look for "Database path:" in output
   ```

4. **Check for multiple instances:**
   - Each Claude window might use different config
   - Project vs global config conflicts

### Issue: Too much memory stored

**Symptoms:**
- Irrelevant data cluttering results
- Slow performance
- Large database size

**Solutions:**

1. **Run aggressive compaction:**
   ```bash
   ison-memory compact --strategy aggressive
   ```

2. **Delete specific entities:**
   ```json
   {
     "tool": "delete_entities",
     "arguments": {
       "entityNames": ["Unwanted Entity 1", "Unwanted Entity 2"]
     }
   }
   ```

3. **Export, filter, reimport:**
   ```bash
   ison-memory export --format ison --output full_backup.ison
   # Manually edit to remove unwanted entries
   # Reimport filtered version
   ```

---

## Platform-Specific Issues

### Claude Desktop Issues

**Issue: Server not recognized**

```json
// Check config syntax
{
  "mcpServers": {
    "ison-memory": {
      "command": "ison-memory",  // Must be in PATH
      "args": ["serve"]
    }
  }
}
```

**Issue: Wrong Python version**

```json
// Specify full path to Python
{
  "mcpServers": {
    "ison-memory": {
      "command": "/usr/local/bin/python3.10",
      "args": ["-m", "ison_memory_mcp.cli", "serve"]
    }
  }
}
```

### Claude Code CLI Issues

**Issue: MCP server not loading**

```bash
# Verify MCP server is registered
claude mcp list

# Add if missing
claude mcp add ison-memory -- ison-memory serve
```

**Issue: Project config not working**

```bash
# Check file location
ls -la .mcp.json

# Verify JSON syntax
python -m json.tool .mcp.json
```

### Windows-Specific Issues

**Issue: Path separators**

```json
// Use forward slashes or escaped backslashes
{
  "env": {
    "ISON_MEMORY_STORAGE_PATH": "C:/Users/Name/.ison-memory/memory.db"
    // or
    "ISON_MEMORY_STORAGE_PATH": "C:\\Users\\Name\\.ison-memory\\memory.db"
  }
}
```

**Issue: Long path errors**

```powershell
# Enable long paths in Windows
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

### macOS-Specific Issues

**Issue: Gatekeeper blocking**

```bash
# Allow app to run
xattr -d com.apple.quarantine $(which ison-memory)
```

**Issue: Permission denied on Library folder**

```bash
# Grant full disk access to Terminal/IDE in System Preferences
# System Preferences → Security & Privacy → Privacy → Full Disk Access
```

---

## Performance Issues

### Issue: Slow startup

**Solutions:**

1. **Reduce cache size:**
   ```toml
   [storage]
   cache_size = 500
   ```

2. **Disable auto-reindex:**
   ```toml
   [index]
   auto_reindex = false
   ```

3. **Use smaller database:**
   ```bash
   ison-memory compact --strategy aggressive
   ```

### Issue: High memory usage

**Solutions:**

1. **Reduce cache:**
   ```toml
   [storage]
   cache_size = 500  # ~2MB instead of ~8MB
   ```

2. **Disable compression buffer:**
   ```toml
   [backup]
   compress = false
   ```

### Issue: Slow queries

**Solutions:**

1. **Add indexes manually:**
   ```bash
   sqlite3 ~/.ison-memory/memory.db "CREATE INDEX IF NOT EXISTS idx_obs_content ON observations(content);"
   ```

2. **Optimize database:**
   ```bash
   sqlite3 ~/.ison-memory/memory.db "VACUUM; ANALYZE;"
   ```

3. **Limit query scope:**
   ```json
   {"maxResults": 10, "entityType": "person"}
   ```

---

## Debug Mode

### Enable Debug Logging

```bash
# Via command line
ison-memory serve --log-level debug

# Via environment variable
ISON_MEMORY_SERVER_LOG_LEVEL=debug ison-memory serve

# Via config file
[server]
log_level = "debug"
```

### View Logs

```bash
# Real-time log viewing
tail -f ~/.ison-memory/logs/server.log

# Search for errors
grep -i error ~/.ison-memory/logs/server.log

# Last 100 lines
tail -100 ~/.ison-memory/logs/server.log
```

### Debug SQL Queries

```bash
# Enable SQLite tracing
ISON_MEMORY_DEBUG_SQL=1 ison-memory serve --log-level debug
```

### Test Tool Calls

```bash
# Test search
echo '{"query": "test"}' | ison-memory serve --test-tool search_memory

# Test stats
ison-memory serve --test-tool memory_stats
```

---

## Getting Help

### Gather Diagnostic Information

Before reporting an issue, collect:

```bash
# Version info
ison-memory --version
python --version
pip show ison-memory-mcp

# Configuration
ison-memory config

# Statistics
ison-memory stats

# Recent logs
tail -50 ~/.ison-memory/logs/server.log
```

### Report an Issue

1. **GitHub Issues**: [github.com/anthropics/ison-memory-mcp/issues](https://github.com/anthropics/ison-memory-mcp/issues)

2. **Include:**
   - Operating system and version
   - Python version
   - Package version
   - Configuration (redact sensitive info)
   - Error messages and logs
   - Steps to reproduce

### Community Resources

- **Documentation**: [docs/](.)
- **Examples**: [Use Cases](USE-CASES.md)
- **API Reference**: [API Reference](API-REFERENCE.md)

---

## Recovery Procedures

### Complete Reset

```bash
# Backup first
cp -r ~/.ison-memory ~/.ison-memory.backup

# Remove all data
rm -rf ~/.ison-memory

# Reinitialize
ison-memory init

# Start fresh
ison-memory serve
```

### Restore from Backup

```bash
# List backups
ison-memory backups

# Restore specific backup
gunzip -c ~/.ison-memory/backups/backup_20250115_060000.db.gz > ~/.ison-memory/memory.db

# Verify restoration
ison-memory stats
```

### Export for Migration

```bash
# Export full graph
ison-memory export --format ison --output migration.ison

# On new system, import
# (Copy migration.ison to new system)
# (Future: ison-memory import migration.ison)
```

---

This troubleshooting guide covers common issues with ISON Memory MCP. For architecture details, see [Architecture](ARCHITECTURE.md). For configuration help, see [Configuration](CONFIGURATION.md).
