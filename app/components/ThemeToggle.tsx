'use client';

import React, { useState, useEffect } from 'react';
import { Sun, Moon } from 'lucide-react';

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('mlops_theme');
    if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    }
  }, []);

  const toggle = () => {
    setIsDark(prev => {
      const next = !prev;
      if (next) {
        document.documentElement.classList.add('dark');
        localStorage.setItem('mlops_theme', 'dark');
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('mlops_theme', 'light');
      }
      return next;
    });
  };

  return (
    <button
      onClick={toggle}
      className="p-2 rounded-xl hover:bg-sky-100/60 dark:hover:bg-sky-800/40 transition-colors duration-200"
      aria-label="Toggle theme"
    >
      {isDark ? (
        <Sun className="w-[18px] h-[18px] text-sky-300" />
      ) : (
        <Moon className="w-[18px] h-[18px] text-sky-700" />
      )}
    </button>
  );
}
