/**
 * User Store — Hardcoded users for development/demo
 * ===================================================
 * In production, replace with LDAP/Active Directory integration.
 */

export type UserRole = 'admin' | 'operator' | 'viewer';

export interface User {
  username: string;
  password: string; // In production: bcrypt hash
  role: UserRole;
  displayName: string;
}

/**
 * Hardcoded user store for development.
 * Roles:
 *   admin    — full access (config, acknowledge alarms, control)
 *   operator — can acknowledge alarms, view all data, limited control
 *   viewer   — read-only access to dashboards and data
 */
export const users: User[] = [
  {
    username: 'admin',
    password: 'admin123',
    role: 'admin',
    displayName: 'System Admin',
  },
  {
    username: 'operator',
    password: 'oper123',
    role: 'operator',
    displayName: 'Plant Operator',
  },
  {
    username: 'viewer',
    password: 'view123',
    role: 'viewer',
    displayName: 'Read-Only Viewer',
  },
];

/**
 * Find a user by username.
 */
export function findUser(username: string): User | undefined {
  return users.find(u => u.username === username);
}

/**
 * Validate credentials. Returns user if valid, undefined otherwise.
 */
export function validateCredentials(username: string, password: string): User | undefined {
  const user = findUser(username);
  if (user && user.password === password) {
    return user;
  }
  return undefined;
}

/**
 * Role hierarchy — checks if role has required permission level.
 */
const roleHierarchy: Record<UserRole, number> = {
  viewer: 1,
  operator: 2,
  admin: 3,
};

export function hasPermission(userRole: UserRole, requiredRole: UserRole): boolean {
  return roleHierarchy[userRole] >= roleHierarchy[requiredRole];
}
