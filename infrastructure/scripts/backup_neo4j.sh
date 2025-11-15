#!/usr/bin/env bash
# =============================================================================
# Neo4j Automated Backup Script
# =============================================================================
#
# This script performs automated backups of Neo4j database using neo4j-admin dump.
# Features:
#   - Full database dump with compression
#   - Automatic rotation (delete backups older than retention period)
#   - Lock file to prevent concurrent backups
#   - Validation of backup integrity
#   - Email notifications on failure (optional)
#   - Backup to local disk (with optional cloud upload)
#
# Usage:
#   bash infrastructure/scripts/backup_neo4j.sh [--retention-days N]
#
# Cron setup (daily at 3 AM):
#   0 3 * * * /path/to/backup_neo4j.sh >> /var/log/neo4j_backup.log 2>&1
#
# Environment variables (from .env.production):
#   - NEO4J_BACKUP_DIR: Backup destination directory
#   - NEO4J_BACKUP_RETENTION_DAYS: Days to keep backups (default: 30)
#   - NEO4J_BACKUP_EMAIL: Email for failure notifications (optional)
#   - NEO4J_DATABASE_NAME: Database name to backup (default: merl-t-kg)
#
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration (can be overridden by .env.production)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env.production"

# Default values
DEFAULT_BACKUP_DIR="${PROJECT_ROOT}/backups/neo4j"
DEFAULT_RETENTION_DAYS=30
DEFAULT_DATABASE_NAME="merl-t-kg"
CONTAINER_NAME="merl-t-neo4j-production"

# Load environment variables if .env.production exists
if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck disable=SC1090
    source <(grep -E '^(NEO4J_BACKUP_DIR|NEO4J_BACKUP_RETENTION_DAYS|NEO4J_DATABASE_NAME|NEO4J_BACKUP_EMAIL)=' "${ENV_FILE}" | sed 's/^/export /')
fi

# Set final values (env vars override defaults)
BACKUP_DIR="${NEO4J_BACKUP_DIR:-$DEFAULT_BACKUP_DIR}"
RETENTION_DAYS="${NEO4J_BACKUP_RETENTION_DAYS:-$DEFAULT_RETENTION_DAYS}"
DATABASE_NAME="${NEO4J_DATABASE_NAME:-$DEFAULT_DATABASE_NAME}"
BACKUP_EMAIL="${NEO4J_BACKUP_EMAIL:-}"

# Backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILENAME="neo4j_${DATABASE_NAME}_${TIMESTAMP}.dump"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"
BACKUP_PATH_GZ="${BACKUP_PATH}.gz"
LOCK_FILE="${BACKUP_DIR}/.backup_lock"

# Backup metadata
METADATA_FILE="${BACKUP_DIR}/${BACKUP_FILENAME}.metadata.json"

# =============================================================================
# Functions
# =============================================================================

print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}  Neo4j Automated Backup - $(date)${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

check_dependencies() {
    print_info "Checking dependencies..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker."
        exit 1
    fi

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running."
        exit 1
    fi

    # Check if Neo4j container exists
    if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_error "Neo4j container '${CONTAINER_NAME}' not found."
        print_info "Available containers:"
        docker ps -a --format 'table {{.Names}}\t{{.Status}}'
        exit 1
    fi

    # Check if Neo4j container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_error "Neo4j container '${CONTAINER_NAME}' is not running."
        docker ps -a --filter "name=${CONTAINER_NAME}" --format 'table {{.Names}}\t{{.Status}}'
        exit 1
    fi

    print_info "All dependencies satisfied."
}

create_backup_directory() {
    print_info "Creating backup directory: ${BACKUP_DIR}"
    mkdir -p "${BACKUP_DIR}"
    chmod 755 "${BACKUP_DIR}"
}

acquire_lock() {
    print_info "Acquiring backup lock..."

    if [[ -f "${LOCK_FILE}" ]]; then
        local lock_pid
        lock_pid=$(cat "${LOCK_FILE}")

        # Check if process is still running
        if ps -p "${lock_pid}" > /dev/null 2>&1; then
            print_error "Another backup is already running (PID: ${lock_pid})"
            exit 1
        else
            print_warn "Stale lock file found. Removing..."
            rm -f "${LOCK_FILE}"
        fi
    fi

    # Create lock file with current PID
    echo $$ > "${LOCK_FILE}"
    print_info "Lock acquired (PID: $$)"
}

release_lock() {
    if [[ -f "${LOCK_FILE}" ]]; then
        rm -f "${LOCK_FILE}"
        print_info "Lock released"
    fi
}

perform_backup() {
    print_info "Starting Neo4j database dump..."
    print_info "Database: ${DATABASE_NAME}"
    print_info "Backup file: ${BACKUP_PATH}"

    local start_time
    start_time=$(date +%s)

    # Execute neo4j-admin dump inside container
    if docker exec "${CONTAINER_NAME}" \
        neo4j-admin database dump \
        --database="${DATABASE_NAME}" \
        --to-path=/backups \
        --overwrite-destination=true \
        "${BACKUP_FILENAME}" 2>&1; then

        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))

        print_info "Database dump completed in ${duration} seconds"
    else
        print_error "Database dump failed"
        return 1
    fi
}

compress_backup() {
    print_info "Compressing backup..."

    if [[ ! -f "${BACKUP_PATH}" ]]; then
        print_error "Backup file not found: ${BACKUP_PATH}"
        return 1
    fi

    local original_size
    original_size=$(du -h "${BACKUP_PATH}" | cut -f1)
    print_info "Original size: ${original_size}"

    local start_time
    start_time=$(date +%s)

    if gzip -9 "${BACKUP_PATH}"; then
        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))

        local compressed_size
        compressed_size=$(du -h "${BACKUP_PATH_GZ}" | cut -f1)

        print_info "Compression completed in ${duration} seconds"
        print_info "Compressed size: ${compressed_size}"

        return 0
    else
        print_error "Compression failed"
        return 1
    fi
}

validate_backup() {
    print_info "Validating backup integrity..."

    if [[ ! -f "${BACKUP_PATH_GZ}" ]]; then
        print_error "Backup file not found: ${BACKUP_PATH_GZ}"
        return 1
    fi

    # Test gzip integrity
    if gzip -t "${BACKUP_PATH_GZ}" 2>&1; then
        print_info "✓ Backup archive is valid"
    else
        print_error "✗ Backup archive is corrupted"
        return 1
    fi

    # Check file size (should be > 0)
    local file_size
    file_size=$(stat -f%z "${BACKUP_PATH_GZ}" 2>/dev/null || stat -c%s "${BACKUP_PATH_GZ}" 2>/dev/null)

    if [[ ${file_size} -gt 0 ]]; then
        print_info "✓ Backup file size: $(numfmt --to=iec-i --suffix=B "${file_size}" 2>/dev/null || echo "${file_size} bytes")"
    else
        print_error "✗ Backup file is empty"
        return 1
    fi

    return 0
}

create_metadata() {
    print_info "Creating backup metadata..."

    local file_size
    file_size=$(stat -f%z "${BACKUP_PATH_GZ}" 2>/dev/null || stat -c%s "${BACKUP_PATH_GZ}" 2>/dev/null)

    local checksum
    checksum=$(sha256sum "${BACKUP_PATH_GZ}" 2>/dev/null | awk '{print $1}' || shasum -a 256 "${BACKUP_PATH_GZ}" | awk '{print $1}')

    # Get Neo4j version and node/relationship counts
    local neo4j_version
    neo4j_version=$(docker exec "${CONTAINER_NAME}" neo4j --version 2>&1 | head -1 || echo "unknown")

    local node_count
    node_count=$(docker exec "${CONTAINER_NAME}" \
        cypher-shell -u neo4j -p "${NEO4J_AUTH#*/}" \
        "MATCH (n) RETURN count(n) AS count;" 2>/dev/null | tail -2 | head -1 | tr -d '"' || echo "0")

    local rel_count
    rel_count=$(docker exec "${CONTAINER_NAME}" \
        cypher-shell -u neo4j -p "${NEO4J_AUTH#*/}" \
        "MATCH ()-[r]->() RETURN count(r) AS count;" 2>/dev/null | tail -2 | head -1 | tr -d '"' || echo "0")

    # Create JSON metadata
    cat > "${METADATA_FILE}" <<EOF
{
  "backup_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "database_name": "${DATABASE_NAME}",
  "neo4j_version": "${neo4j_version}",
  "backup_file": "${BACKUP_FILENAME}.gz",
  "file_size_bytes": ${file_size},
  "file_size_human": "$(du -h "${BACKUP_PATH_GZ}" | cut -f1)",
  "sha256_checksum": "${checksum}",
  "node_count": ${node_count},
  "relationship_count": ${rel_count},
  "backup_script_version": "1.0.0",
  "hostname": "$(hostname)"
}
EOF

    print_info "Metadata saved: ${METADATA_FILE}"
}

rotate_old_backups() {
    print_info "Rotating old backups (retention: ${RETENTION_DAYS} days)..."

    local deleted_count=0

    # Find and delete backups older than retention period
    while IFS= read -r -d '' old_backup; do
        print_info "Deleting old backup: $(basename "${old_backup}")"
        rm -f "${old_backup}"
        rm -f "${old_backup}.metadata.json"
        ((deleted_count++))
    done < <(find "${BACKUP_DIR}" -name "neo4j_*.dump.gz" -type f -mtime "+${RETENTION_DAYS}" -print0 2>/dev/null)

    if [[ ${deleted_count} -gt 0 ]]; then
        print_info "Deleted ${deleted_count} old backup(s)"
    else
        print_info "No old backups to delete"
    fi
}

send_notification() {
    local status=$1
    local message=$2

    if [[ -z "${BACKUP_EMAIL}" ]]; then
        return 0
    fi

    print_info "Sending email notification to ${BACKUP_EMAIL}"

    local subject
    if [[ "${status}" == "success" ]]; then
        subject="✓ Neo4j Backup Success - ${TIMESTAMP}"
    else
        subject="✗ Neo4j Backup FAILED - ${TIMESTAMP}"
    fi

    # Send email using mail command (requires mailutils or similar)
    if command -v mail &> /dev/null; then
        echo "${message}" | mail -s "${subject}" "${BACKUP_EMAIL}"
        print_info "Email sent successfully"
    else
        print_warn "mail command not found. Install mailutils to enable email notifications."
    fi
}

cleanup_on_error() {
    print_error "Backup failed. Cleaning up..."

    # Remove incomplete backup files
    if [[ -f "${BACKUP_PATH}" ]]; then
        rm -f "${BACKUP_PATH}"
        print_info "Removed incomplete backup: ${BACKUP_PATH}"
    fi

    if [[ -f "${BACKUP_PATH_GZ}" ]]; then
        rm -f "${BACKUP_PATH_GZ}"
        print_info "Removed incomplete backup: ${BACKUP_PATH_GZ}"
    fi

    if [[ -f "${METADATA_FILE}" ]]; then
        rm -f "${METADATA_FILE}"
        print_info "Removed incomplete metadata: ${METADATA_FILE}"
    fi

    release_lock
}

# =============================================================================
# Main execution
# =============================================================================

main() {
    print_header

    # Set up error handling
    trap cleanup_on_error ERR EXIT

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --retention-days)
                RETENTION_DAYS="$2"
                shift 2
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Usage: $0 [--retention-days N]"
                exit 1
                ;;
        esac
    done

    check_dependencies
    create_backup_directory
    acquire_lock

    # Perform backup
    if perform_backup && compress_backup && validate_backup; then
        create_metadata
        rotate_old_backups

        # Clear error trap on success
        trap - ERR EXIT
        release_lock

        print_info "Backup completed successfully!"
        print_info "Backup file: ${BACKUP_PATH_GZ}"

        # Send success notification
        local success_message="Neo4j backup completed successfully.

Backup Details:
- Database: ${DATABASE_NAME}
- Timestamp: ${TIMESTAMP}
- File: ${BACKUP_FILENAME}.gz
- Size: $(du -h "${BACKUP_PATH_GZ}" | cut -f1)
- Location: ${BACKUP_DIR}

Next backup: Tomorrow at $(date -d 'tomorrow 3:00' '+%Y-%m-%d %H:%M' 2>/dev/null || date -v+1d -v3H -v0M '+%Y-%m-%d %H:%M' 2>/dev/null || echo '3:00 AM')"

        send_notification "success" "${success_message}"

        exit 0
    else
        # Backup failed
        local error_message="Neo4j backup FAILED.

Database: ${DATABASE_NAME}
Timestamp: ${TIMESTAMP}
Error: See logs for details

Please investigate immediately."

        send_notification "failure" "${error_message}"

        print_error "Backup failed!"
        exit 1
    fi
}

# Run main function
main "$@"
