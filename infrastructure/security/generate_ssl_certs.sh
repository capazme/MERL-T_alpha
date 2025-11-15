#!/usr/bin/env bash
# =============================================================================
# Neo4j SSL/TLS Certificate Generation Script
# =============================================================================
#
# This script generates self-signed SSL/TLS certificates for Neo4j Bolt protocol.
# For production with public exposure, use Let's Encrypt instead.
#
# Usage:
#   bash infrastructure/security/generate_ssl_certs.sh
#
# Generated files:
#   - infrastructure/security/neo4j/ssl/bolt.key (private key)
#   - infrastructure/security/neo4j/ssl/bolt.crt (public certificate)
#   - infrastructure/security/neo4j/ssl/bolt_ca.crt (CA certificate, optional)
#
# Requirements:
#   - OpenSSL installed (brew install openssl on macOS)
#
# Security notes:
#   - Self-signed certs are suitable for development/staging/internal networks
#   - For production with public internet: use Let's Encrypt (certbot)
#   - Keep bolt.key private and secure (chmod 600)
#   - Certificate validity: 365 days (renew annually)
#
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="${SCRIPT_DIR}/neo4j/ssl"
CERT_VALIDITY_DAYS=365
KEY_SIZE=4096

# Certificate subject details
COUNTRY="IT"
STATE="Lazio"
CITY="Rome"
ORGANIZATION="ALIS - Artificial Legal Intelligence Society"
ORGANIZATIONAL_UNIT="MERL-T Knowledge Graph"
COMMON_NAME="merl-t-neo4j-production"
EMAIL="admin@merl-t.ai"

# =============================================================================
# Functions
# =============================================================================

print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}  Neo4j SSL/TLS Certificate Generation${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    print_info "Checking dependencies..."

    if ! command -v openssl &> /dev/null; then
        print_error "OpenSSL not found. Please install it:"
        echo "  macOS: brew install openssl"
        echo "  Ubuntu: sudo apt-get install openssl"
        echo "  CentOS: sudo yum install openssl"
        exit 1
    fi

    local openssl_version
    openssl_version=$(openssl version | awk '{print $2}')
    print_info "OpenSSL version: ${openssl_version}"
}

create_directories() {
    print_info "Creating SSL directory: ${SSL_DIR}"
    mkdir -p "${SSL_DIR}"
    chmod 755 "${SSL_DIR}"
}

backup_existing_certs() {
    if [[ -f "${SSL_DIR}/bolt.key" ]] || [[ -f "${SSL_DIR}/bolt.crt" ]]; then
        print_warn "Existing certificates found. Creating backup..."
        local backup_dir="${SSL_DIR}/backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "${backup_dir}"

        if [[ -f "${SSL_DIR}/bolt.key" ]]; then
            mv "${SSL_DIR}/bolt.key" "${backup_dir}/"
            print_info "Backed up bolt.key to ${backup_dir}/"
        fi

        if [[ -f "${SSL_DIR}/bolt.crt" ]]; then
            mv "${SSL_DIR}/bolt.crt" "${backup_dir}/"
            print_info "Backed up bolt.crt to ${backup_dir}/"
        fi

        if [[ -f "${SSL_DIR}/bolt_ca.crt" ]]; then
            mv "${SSL_DIR}/bolt_ca.crt" "${backup_dir}/"
            print_info "Backed up bolt_ca.crt to ${backup_dir}/"
        fi
    fi
}

generate_private_key() {
    print_info "Generating ${KEY_SIZE}-bit RSA private key..."

    openssl genrsa \
        -out "${SSL_DIR}/bolt.key" \
        ${KEY_SIZE} \
        2>/dev/null

    # Secure permissions (readable only by owner)
    chmod 600 "${SSL_DIR}/bolt.key"

    print_info "Private key generated: ${SSL_DIR}/bolt.key"
}

generate_self_signed_certificate() {
    print_info "Generating self-signed certificate (valid for ${CERT_VALIDITY_DAYS} days)..."

    # Create certificate subject
    local subject="/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORGANIZATION}/OU=${ORGANIZATIONAL_UNIT}/CN=${COMMON_NAME}/emailAddress=${EMAIL}"

    # Generate self-signed certificate
    openssl req \
        -new \
        -x509 \
        -key "${SSL_DIR}/bolt.key" \
        -out "${SSL_DIR}/bolt.crt" \
        -days ${CERT_VALIDITY_DAYS} \
        -subj "${subject}" \
        -addext "subjectAltName=DNS:${COMMON_NAME},DNS:localhost,DNS:neo4j,IP:127.0.0.1" \
        2>/dev/null

    chmod 644 "${SSL_DIR}/bolt.crt"

    print_info "Certificate generated: ${SSL_DIR}/bolt.crt"
}

generate_ca_certificate() {
    print_info "Generating Certificate Authority (CA) certificate..."

    # For self-signed certs, CA is same as cert
    cp "${SSL_DIR}/bolt.crt" "${SSL_DIR}/bolt_ca.crt"
    chmod 644 "${SSL_DIR}/bolt_ca.crt"

    print_info "CA certificate generated: ${SSL_DIR}/bolt_ca.crt"
}

verify_certificates() {
    print_info "Verifying generated certificates..."

    # Verify private key
    if openssl rsa -in "${SSL_DIR}/bolt.key" -check -noout 2>/dev/null; then
        print_info "✓ Private key is valid"
    else
        print_error "✗ Private key is invalid"
        return 1
    fi

    # Verify certificate
    if openssl x509 -in "${SSL_DIR}/bolt.crt" -text -noout &>/dev/null; then
        print_info "✓ Certificate is valid"

        # Display certificate info
        local expiry_date
        expiry_date=$(openssl x509 -in "${SSL_DIR}/bolt.crt" -enddate -noout | cut -d= -f2)
        print_info "  Expires: ${expiry_date}"

        local subject
        subject=$(openssl x509 -in "${SSL_DIR}/bolt.crt" -subject -noout | sed 's/subject=//')
        print_info "  Subject: ${subject}"

        # Check if certificate matches private key
        local key_modulus
        local cert_modulus
        key_modulus=$(openssl rsa -in "${SSL_DIR}/bolt.key" -modulus -noout 2>/dev/null | md5)
        cert_modulus=$(openssl x509 -in "${SSL_DIR}/bolt.crt" -modulus -noout | md5)

        if [[ "${key_modulus}" == "${cert_modulus}" ]]; then
            print_info "✓ Certificate matches private key"
        else
            print_error "✗ Certificate does NOT match private key"
            return 1
        fi
    else
        print_error "✗ Certificate is invalid"
        return 1
    fi
}

print_usage_instructions() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}  SSL/TLS Setup Complete${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
    echo -e "${GREEN}Generated files:${NC}"
    echo "  📄 Private key:  ${SSL_DIR}/bolt.key"
    echo "  📄 Certificate:  ${SSL_DIR}/bolt.crt"
    echo "  📄 CA cert:      ${SSL_DIR}/bolt_ca.crt"
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "  1. Update .env.production:"
    echo "     NEO4J_SSL_ENABLED=true"
    echo "     NEO4J_SSL_DIR=${SSL_DIR}"
    echo ""
    echo "  2. Restart Neo4j:"
    echo "     docker-compose --env-file .env.production \\"
    echo "       -f infrastructure/docker/neo4j-production.yml restart"
    echo ""
    echo "  3. Test Bolt connection with TLS:"
    echo "     cypher-shell -a neo4j+s://localhost:7687 -u neo4j -p <password>"
    echo ""
    echo -e "${YELLOW}Security reminders:${NC}"
    echo "  ⚠️  Keep bolt.key private (chmod 600)"
    echo "  ⚠️  Never commit bolt.key to version control"
    echo "  ⚠️  Renew certificate before expiry (${CERT_VALIDITY_DAYS} days)"
    echo "  ⚠️  For production with public internet, use Let's Encrypt"
    echo ""
    echo -e "${BLUE}For Let's Encrypt (certbot):${NC}"
    echo "  certbot certonly --standalone -d ${COMMON_NAME}"
    echo "  cp /etc/letsencrypt/live/${COMMON_NAME}/privkey.pem ${SSL_DIR}/bolt.key"
    echo "  cp /etc/letsencrypt/live/${COMMON_NAME}/fullchain.pem ${SSL_DIR}/bolt.crt"
    echo ""
}

# =============================================================================
# Main execution
# =============================================================================

main() {
    print_header

    check_dependencies
    create_directories
    backup_existing_certs

    generate_private_key
    generate_self_signed_certificate
    generate_ca_certificate

    if verify_certificates; then
        print_usage_instructions
        exit 0
    else
        print_error "Certificate generation failed verification"
        exit 1
    fi
}

# Run main function
main "$@"
