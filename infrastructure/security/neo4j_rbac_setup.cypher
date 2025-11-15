// =============================================================================
// Neo4j Role-Based Access Control (RBAC) Setup
// =============================================================================
//
// This script creates multiple users with different privilege levels for
// secure access to the MERL-T Knowledge Graph.
//
// Users created:
//   1. neo4j (admin) - Full database admin (existing default user)
//   2. merl_t_read  - Read-only access (query operations)
//   3. merl_t_write - Read + Write access (data ingestion)
//   4. merl_t_app   - Application user (backend services)
//
// Roles:
//   - admin: Full control (CREATE, DELETE, all operations)
//   - reader: Read-only (MATCH, RETURN queries)
//   - writer: Read + Write (MATCH, CREATE, MERGE, no DELETE)
//
// Usage:
//   # Connect as admin
//   cypher-shell -u neo4j -p <admin_password> < infrastructure/security/neo4j_rbac_setup.cypher
//
//   # Or via Docker
//   docker exec -i merl-t-neo4j-production \
//     cypher-shell -u neo4j -p <admin_password> < infrastructure/security/neo4j_rbac_setup.cypher
//
// Security best practices:
//   - Use strong passwords (20+ characters, mixed case, numbers, symbols)
//   - Rotate passwords every 90 days
//   - Never hardcode passwords in code (use environment variables)
//   - Audit user activity via NEO4J_dbms_logs_security_enabled=true
//
// =============================================================================

// =============================================================================
// 1. CREATE CUSTOM ROLES
// =============================================================================

// Create READ-ONLY role (for query operations)
CREATE ROLE merl_t_reader IF NOT EXISTS;

// Grant read permissions to reader role
GRANT ACCESS ON DATABASE `merl-t-kg` TO merl_t_reader;
GRANT MATCH {*} ON GRAPH `merl-t-kg` TO merl_t_reader;
GRANT READ {*} ON GRAPH `merl-t-kg` TO merl_t_reader;

// Grant SHOW procedures (for schema inspection)
GRANT EXECUTE PROCEDURE db.schema.* ON DBMS TO merl_t_reader;
GRANT EXECUTE PROCEDURE db.labels ON DBMS TO merl_t_reader;
GRANT EXECUTE PROCEDURE db.relationshipTypes ON DBMS TO merl_t_reader;
GRANT EXECUTE PROCEDURE db.propertyKeys ON DBMS TO merl_t_reader;
GRANT EXECUTE PROCEDURE db.indexes ON DBMS TO merl_t_reader;
GRANT EXECUTE PROCEDURE db.constraints ON DBMS TO merl_t_reader;

// Grant APOC read-only procedures
GRANT EXECUTE PROCEDURE apoc.* ON DBMS TO merl_t_reader;

// Create WRITER role (for data ingestion)
CREATE ROLE merl_t_writer IF NOT EXISTS;

// Grant write permissions to writer role
GRANT ACCESS ON DATABASE `merl-t-kg` TO merl_t_writer;
GRANT MATCH {*} ON GRAPH `merl-t-kg` TO merl_t_writer;
GRANT READ {*} ON GRAPH `merl-t-kg` TO merl_t_writer;
GRANT CREATE {*} ON GRAPH `merl-t-kg` TO merl_t_writer;
GRANT SET PROPERTY {*} ON GRAPH `merl-t-kg` TO merl_t_writer;
GRANT REMOVE PROPERTY {*} ON GRAPH `merl-t-kg` TO merl_t_writer;

// Grant MERGE (for upsert operations)
GRANT MERGE {*} ON GRAPH `merl-t-kg` TO merl_t_writer;

// Grant APOC write procedures (for batch operations)
GRANT EXECUTE PROCEDURE apoc.* ON DBMS TO merl_t_writer;
GRANT EXECUTE PROCEDURE apoc.periodic.* ON DBMS TO merl_t_writer;
GRANT EXECUTE PROCEDURE apoc.load.* ON DBMS TO merl_t_writer;

// Note: DELETE permission is NOT granted to writer role
// Only admin can delete nodes/relationships

// =============================================================================
// 2. CREATE USERS
// =============================================================================

// Create READ-ONLY user (for application queries)
// Default password: CHANGE_ME_READ - MUST be changed immediately
CREATE USER merl_t_read IF NOT EXISTS
  SET PASSWORD 'CHANGE_ME_READ'
  CHANGE NOT REQUIRED;

// Assign reader role
GRANT ROLE merl_t_reader TO merl_t_read;

// Create WRITE user (for data ingestion pipelines)
// Default password: CHANGE_ME_WRITE - MUST be changed immediately
CREATE USER merl_t_write IF NOT EXISTS
  SET PASSWORD 'CHANGE_ME_WRITE'
  CHANGE NOT REQUIRED;

// Assign writer role
GRANT ROLE merl_t_writer TO merl_t_write;

// Create APPLICATION user (for backend services - read + limited write)
// Default password: CHANGE_ME_APP - MUST be changed immediately
CREATE USER merl_t_app IF NOT EXISTS
  SET PASSWORD 'CHANGE_ME_APP'
  CHANGE NOT REQUIRED;

// Assign both reader and writer roles (full read + write, no delete)
GRANT ROLE merl_t_reader TO merl_t_app;
GRANT ROLE merl_t_writer TO merl_t_app;

// =============================================================================
// 3. VERIFY SETUP
// =============================================================================

// Show all users
SHOW USERS;

// Show all roles
SHOW ROLES;

// Show role assignments
SHOW USER merl_t_read PRIVILEGES;
SHOW USER merl_t_write PRIVILEGES;
SHOW USER merl_t_app PRIVILEGES;

// =============================================================================
// 4. PASSWORD CHANGE INSTRUCTIONS
// =============================================================================

// After running this script, immediately change passwords:
//
// ALTER USER merl_t_read SET PASSWORD 'new_strong_password_here';
// ALTER USER merl_t_write SET PASSWORD 'new_strong_password_here';
// ALTER USER merl_t_app SET PASSWORD 'new_strong_password_here';
//
// Generate strong passwords with:
//   openssl rand -base64 32
//
// Store passwords securely:
//   - Use environment variables (never hardcode)
//   - Use secrets management (HashiCorp Vault, AWS Secrets Manager)
//   - Rotate passwords every 90 days
//
// =============================================================================

// =============================================================================
// 5. CONNECTION EXAMPLES
// =============================================================================

// Connect as read-only user (query operations)
// :server connect neo4j+s://localhost:7687 -u merl_t_read -p <password>
//
// Test read access:
// MATCH (n:Norma) RETURN count(n) LIMIT 10;
//
// Test write denial (should fail):
// CREATE (n:Test {name: 'should_fail'});
// Error: Permission denied

// Connect as write user (data ingestion)
// :server connect neo4j+s://localhost:7687 -u merl_t_write -p <password>
//
// Test write access:
// CREATE (n:Test {name: 'test'}) RETURN n;
//
// Test delete denial (should fail):
// MATCH (n:Test) DELETE n;
// Error: Permission denied

// Connect as application user (backend services)
// :server connect neo4j+s://localhost:7687 -u merl_t_app -p <password>
//
// Full read + write access (no delete)

// =============================================================================
// END OF RBAC SETUP
// =============================================================================
