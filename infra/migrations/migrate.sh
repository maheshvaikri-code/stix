#!/bin/bash
# STIX Database Migration Script
# Usage: ./migrate.sh [up|down|version|create] [options]

set -e

# Configuration
MIGRATIONS_DIR="$(dirname "$0")"
DATABASE_URL="${DATABASE_URL:-postgresql://stix:stix@localhost:5432/stix}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get current version
get_current_version() {
    psql "$DATABASE_URL" -t -c "SELECT COALESCE(MAX(version), 0) FROM schema_migrations WHERE NOT dirty" 2>/dev/null || echo "0"
}

# Get all migration files
get_migrations() {
    local direction=$1
    ls -1 "$MIGRATIONS_DIR"/*.${direction}.sql 2>/dev/null | sort -t '_' -k1 -n
}

# Apply a single migration
apply_migration() {
    local file=$1
    local version=$(basename "$file" | cut -d '_' -f1)

    log_info "Applying migration $version: $(basename "$file")"

    # Mark as dirty
    psql "$DATABASE_URL" -c "INSERT INTO schema_migrations (version, dirty) VALUES ($version, true) ON CONFLICT (version) DO UPDATE SET dirty = true"

    # Apply migration
    if psql "$DATABASE_URL" -f "$file"; then
        # Mark as complete
        psql "$DATABASE_URL" -c "UPDATE schema_migrations SET dirty = false WHERE version = $version"
        log_info "Migration $version completed successfully"
        return 0
    else
        log_error "Migration $version failed!"
        return 1
    fi
}

# Rollback a single migration
rollback_migration() {
    local file=$1
    local version=$(basename "$file" | cut -d '_' -f1)

    log_info "Rolling back migration $version: $(basename "$file")"

    # Apply rollback
    if psql "$DATABASE_URL" -f "$file"; then
        # Remove migration record
        psql "$DATABASE_URL" -c "DELETE FROM schema_migrations WHERE version = $version"
        log_info "Rollback $version completed successfully"
        return 0
    else
        log_error "Rollback $version failed!"
        return 1
    fi
}

# Run all pending up migrations
migrate_up() {
    local target_version=${1:-999999}
    local current_version=$(get_current_version)

    log_info "Current database version: $current_version"
    log_info "Target version: $target_version"

    # Ensure schema_migrations table exists
    psql "$DATABASE_URL" -c "CREATE TABLE IF NOT EXISTS schema_migrations (version BIGINT PRIMARY KEY, dirty BOOLEAN NOT NULL DEFAULT false, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"

    for file in $(get_migrations "up"); do
        local version=$(basename "$file" | cut -d '_' -f1)

        if [ "$version" -gt "$current_version" ] && [ "$version" -le "$target_version" ]; then
            apply_migration "$file" || exit 1
        fi
    done

    log_info "Migration complete. Current version: $(get_current_version)"
}

# Rollback migrations
migrate_down() {
    local steps=${1:-1}
    local current_version=$(get_current_version)

    log_info "Current database version: $current_version"
    log_info "Rolling back $steps migration(s)"

    local count=0
    for file in $(get_migrations "down" | sort -r); do
        local version=$(basename "$file" | cut -d '_' -f1)

        if [ "$version" -le "$current_version" ] && [ "$count" -lt "$steps" ]; then
            rollback_migration "$file" || exit 1
            count=$((count + 1))
        fi
    done

    log_info "Rollback complete. Current version: $(get_current_version)"
}

# Show current version
show_version() {
    echo "Database URL: $DATABASE_URL"
    echo "Current version: $(get_current_version)"

    echo ""
    echo "Applied migrations:"
    psql "$DATABASE_URL" -c "SELECT version, dirty, applied_at FROM schema_migrations ORDER BY version"
}

# Create a new migration
create_migration() {
    local name=$1
    if [ -z "$name" ]; then
        log_error "Migration name required"
        echo "Usage: $0 create <migration_name>"
        exit 1
    fi

    # Get next version number
    local last_version=$(ls -1 "$MIGRATIONS_DIR"/*.up.sql 2>/dev/null | sort -t '_' -k1 -n | tail -1 | xargs basename 2>/dev/null | cut -d '_' -f1)
    local next_version=$(printf "%03d" $((${last_version:-0} + 1)))

    local safe_name=$(echo "$name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
    local up_file="${MIGRATIONS_DIR}/${next_version}_${safe_name}.up.sql"
    local down_file="${MIGRATIONS_DIR}/${next_version}_${safe_name}.down.sql"

    cat > "$up_file" << EOF
-- STIX Database Schema Migration ${next_version}: ${name}
-- Created: $(date -Iseconds)

-- Add your migration SQL here

-- Record this migration
INSERT INTO schema_migrations (version, dirty) VALUES (${next_version}, false)
ON CONFLICT (version) DO NOTHING;
EOF

    cat > "$down_file" << EOF
-- STIX Database Schema Migration ${next_version}: Rollback ${name}

-- Add your rollback SQL here

-- Remove migration record
DELETE FROM schema_migrations WHERE version = ${next_version};
EOF

    log_info "Created migration files:"
    echo "  - $up_file"
    echo "  - $down_file"
}

# Main command handler
case "${1:-up}" in
    up)
        migrate_up "$2"
        ;;
    down)
        migrate_down "$2"
        ;;
    version)
        show_version
        ;;
    create)
        create_migration "$2"
        ;;
    *)
        echo "Usage: $0 [up|down|version|create] [options]"
        echo ""
        echo "Commands:"
        echo "  up [version]     Apply pending migrations (optionally to specific version)"
        echo "  down [steps]     Rollback migrations (default: 1 step)"
        echo "  version          Show current database version"
        echo "  create <name>    Create a new migration"
        echo ""
        echo "Environment:"
        echo "  DATABASE_URL     PostgreSQL connection string"
        exit 1
        ;;
esac
