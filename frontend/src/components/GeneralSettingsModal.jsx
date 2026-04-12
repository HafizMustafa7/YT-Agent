import React from 'react';

export function GeneralSettingsModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-md p-6 bg-white rounded-lg shadow-lg">
        <h2 className="mb-4 text-xl font-bold">General Settings</h2>
        <p className="mb-4">Settings content goes here.</p>
        <button onClick={onClose} className="px-4 py-2 text-white bg-blue-500 rounded">Close</button>
      </div>
    </div>
  );
}
