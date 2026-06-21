/**
 * Login Page — Dark theme matching SCADA app
 * =============================================
 */

import React, { useState } from 'react';
import { useAuthStore } from '../stores/useAuthStore';

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login, isLoading, error } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login(username, password);
  };

  return (
    <div className="min-h-screen bg-surface-1 flex items-center justify-center">
      <div className="w-full max-w-sm">
        {/* Logo / Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-2">
            <div className="w-4 h-4 bg-nvidia rounded-sm" />
            <span className="font-bold text-lg text-nvidia">AI FACTORY SCADA</span>
          </div>
          <p className="text-gray-500 text-sm">Industrial Control System</p>
        </div>

        {/* Login Form */}
        <form
          onSubmit={handleSubmit}
          className="bg-surface-2 border border-surface-4 rounded-lg p-6 space-y-4"
        >
          <h2 className="text-white text-base font-semibold mb-4">Sign In</h2>

          {error && (
            <div className="bg-red-900/30 border border-red-700 rounded px-3 py-2 text-red-300 text-xs">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="username" className="block text-gray-400 text-xs mb-1">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full bg-surface-3 border border-surface-4 rounded px-3 py-2 text-white text-sm
                         focus:outline-none focus:border-nvidia focus:ring-1 focus:ring-nvidia/50
                         placeholder-gray-600"
              placeholder="Enter username"
              autoComplete="username"
              autoFocus
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-gray-400 text-xs mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-surface-3 border border-surface-4 rounded px-3 py-2 text-white text-sm
                         focus:outline-none focus:border-nvidia focus:ring-1 focus:ring-nvidia/50
                         placeholder-gray-600"
              placeholder="Enter password"
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !username || !password}
            className="w-full bg-nvidia hover:bg-nvidia/90 disabled:bg-nvidia/40 disabled:cursor-not-allowed
                       text-black font-semibold text-sm rounded px-4 py-2.5 transition-colors"
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>

          <div className="text-center pt-2">
            <p className="text-gray-600 text-xs">
              Demo credentials: admin / operator / viewer
            </p>
          </div>
        </form>

        <p className="text-gray-700 text-xs text-center mt-4">
          NVIDIA AI Factory Controls v1.0
        </p>
      </div>
    </div>
  );
}
