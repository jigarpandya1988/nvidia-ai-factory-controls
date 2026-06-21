import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Navbar } from './components/common/Navbar';
import { useWebSocket } from './hooks/useWebSocket';
import { Overview } from './pages/Overview';
import { Cooling } from './pages/Cooling';
import { Power } from './pages/Power';
import { Safety } from './pages/Safety';
import { Environment } from './pages/Environment';
import { Trends } from './pages/Trends';
import { Alarms } from './pages/Alarms';

export default function App() {
  useWebSocket(); // Connect on mount

  return (
    <div className="min-h-screen bg-surface-1 text-gray-200 flex flex-col">
      <Navbar />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/cooling" element={<Cooling />} />
          <Route path="/power" element={<Power />} />
          <Route path="/safety" element={<Safety />} />
          <Route path="/environment" element={<Environment />} />
          <Route path="/alarms" element={<Alarms />} />
          <Route path="/trends" element={<Trends />} />
        </Routes>
      </main>
    </div>
  );
}
