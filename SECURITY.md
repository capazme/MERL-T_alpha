# Security Policy

## Supported Versions

We release patches for security vulnerabilities. The following versions are currently being supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.9.x   | :white_check_mark: |
| 0.6.x   | :white_check_mark: |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :x:                |
| < 0.1   | :x:                |

## Reporting a Vulnerability

The ALIS team and community take all security vulnerabilities seriously. Thank you for improving the security of our project. We appreciate your efforts and responsible disclosure and will make every effort to acknowledge your contributions.

### Where to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by email to:
- **Email**: [security@alis.ai](mailto:security@alis.ai)
- **Subject**: `[SECURITY] MERL-T Vulnerability Report`

### What to Include

Please include the following information in your report:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit the issue

This information will help us triage your report more quickly.

### Response Timeline

- **Initial Response**: Within 48 hours of receiving your report
- **Status Update**: Within 7 days with either:
  - Confirmation of the issue and planned fix timeline
  - Rejection with explanation if the issue is not valid
  - Request for additional information
- **Resolution**: Depends on severity
  - **Critical**: Within 7 days
  - **High**: Within 30 days
  - **Medium**: Within 60 days
  - **Low**: Within 90 days

### What to Expect

After you submit a report, we will:

1. **Acknowledge** receipt of your vulnerability report
2. **Confirm** the vulnerability and determine its severity
3. **Develop** a fix and test it thoroughly
4. **Release** a security patch
5. **Publicly disclose** the vulnerability (crediting you if desired)

### Preferred Languages

We prefer all communications to be in English or Italian.

### Safe Harbor

We support safe harbor for security researchers who:

- Make a good faith effort to avoid privacy violations, destruction of data, and interruption or degradation of our services
- Only interact with accounts you own or with explicit permission of the account holder
- Do not exploit a security issue you discover for any reason (including demonstrating additional risk)
- Report vulnerabilities to us as soon as you discover them

We will not pursue legal action against researchers who discover and report vulnerabilities responsibly.

## Security Best Practices

When deploying MERL-T, please follow these security best practices:

### API Keys & Secrets

- **Never** commit API keys, passwords, or secrets to version control
- Use environment variables for all sensitive configuration
- Rotate API keys regularly (recommended: every 90 days)
- Use different API keys for development, staging, and production
- Store secrets in a secure secret management system (HashiCorp Vault, AWS Secrets Manager, etc.)

### Authentication

- Always use HTTPS in production
- Enable rate limiting (already configured)
- Implement IP whitelisting for admin endpoints if possible
- Use strong, unique API keys (minimum 32 characters)
- Monitor for suspicious authentication attempts

### Database Security

- Use strong database passwords
- Enable database encryption at rest
- Use SSL/TLS for database connections
- Regularly backup databases
- Implement proper access controls (least privilege principle)

### Network Security

- Use a firewall to restrict access to services
- Only expose necessary ports (80/443 for web, application-specific ports)
- Use a reverse proxy (nginx, Traefik) for SSL termination
- Enable CORS only for trusted origins
- Implement DDoS protection

### Docker Security

- Run containers as non-root users
- Use official base images
- Scan images for vulnerabilities (Trivy, Clair)
- Keep base images updated
- Use Docker secrets for sensitive data

### Dependency Management

- Regularly update dependencies (`pip-audit`, `safety`)
- Monitor for known vulnerabilities (Dependabot, Snyk)
- Pin dependency versions in production
- Review dependency licenses for compliance

## Disclosure Policy

When we receive a security bug report, we will:

1. Confirm the problem and determine the affected versions
2. Audit code to find any similar problems
3. Prepare fixes for all supported versions
4. Release new security fix versions as soon as possible

We aim to disclose vulnerabilities within 90 days of receiving the report, or sooner if a fix is available.

## Security Updates

To receive security updates:

- **Watch** this repository on GitHub
- **Subscribe** to security announcements at [https://github.com/ALIS-ai/MERL-T/security/advisories](https://github.com/ALIS-ai/MERL-T/security/advisories)
- **Follow** ALIS on Twitter: [@ALIS_ai](https://twitter.com/ALIS_ai)

## Comments on this Policy

If you have suggestions on how this process could be improved, please submit a pull request or open an issue to discuss.

---

**Last Updated**: November 14, 2025
**Version**: 1.0
