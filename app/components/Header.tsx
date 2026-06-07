'use client';

import React, { useState, useEffect } from 'react';
import { Menu, X, ChevronRight, LogOut, User, Cpu, CreditCard } from 'lucide-react';
import Link from 'next/link';
import ThemeToggle from './ThemeToggle';
import { useAuth } from '../context/AuthContext';

export default function Header() {
  const [scrollY, setScrollY] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, isLoggedIn, logout } = useAuth();

  useEffect(() => {
    const h = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', h, { passive: true });
    return () => window.removeEventListener('scroll', h);
  }, []);

  const isScrolled = scrollY > 60;
  const navItems = [
    { label: 'Beranda', href: '/' },
    { label: 'Prediksi', href: '/predict' },
    { label: 'Dashboard', href: '/dashboard' },
  ];

  return (
    <header className="fixed top-0 left-0 right-0 z-50 flex justify-center px-3 md:px-4 pt-3 md:pt-4">
      <div className={`relative w-full md:max-w-5xl rounded-2xl backdrop-blur-2xl transition-all duration-500 ${isScrolled ? 'py-2.5 px-4 md:px-8' : 'py-3 md:py-3.5 px-5 md:px-8'}`}
        style={{
          backgroundColor: isScrolled ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.6)',
          border: `1px solid ${isScrolled ? 'rgba(14,165,233,0.08)' : 'rgba(255,255,255,0.5)'}`,
          boxShadow: isScrolled ? '0 8px 40px rgba(14,165,233,0.12), 0 1px 0 rgba(255,255,255,0.8) inset' : '0 4px 20px rgba(14,165,233,0.06)',
        }}>
        <div className="absolute inset-0 rounded-2xl hidden dark:block" style={{
          backgroundColor: isScrolled ? 'rgba(2,6,23,0.85)' : 'rgba(2,6,23,0.6)',
          border: '1px solid rgba(14,165,233,0.08)',
        }} />

        <div className="relative flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className={`rounded-xl bg-gradient-to-br from-sky-400 to-indigo-600 flex items-center justify-center transition-all duration-300 group-hover:scale-110 group-hover:rotate-3 ${isScrolled ? 'w-7 h-7' : 'w-8 h-8 md:w-9 md:h-9'}`} style={{ boxShadow: '0 4px 12px rgba(14,165,233,0.3)' }}>
              <CreditCard className="w-4 h-4 md:w-5 md:h-5 text-white" />
            </div>
            <span className="text-sm md:text-base font-black text-sky-900 dark:text-sky-100" style={{ letterSpacing: '-0.03em' }}>
              Credit<span className="gradient-text ml-0.5">Care</span>
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-0.5">
            {navItems.map((item) => (
              <Link key={item.label} href={item.href} className="px-3 py-1.5 rounded-xl text-sm font-semibold text-sky-800/60 dark:text-sky-300/60 hover:text-sky-600 dark:hover:text-sky-200 hover:bg-sky-100/40 dark:hover:bg-sky-800/20 transition-all duration-200">
                {item.label}
              </Link>
            ))}
            {isLoggedIn ? (
              <>
                <Link href="/profile" className="px-3 py-1.5 rounded-xl text-sm font-semibold text-sky-800/60 dark:text-sky-300/60 hover:text-sky-600 dark:hover:text-sky-200 hover:bg-sky-100/40 dark:hover:bg-sky-800/20 transition-all">Profil</Link>
                <button onClick={logout} className="px-3 py-1.5 rounded-xl text-sm font-semibold text-red-400/70 hover:text-red-500 hover:bg-red-50/50 dark:hover:bg-red-900/10 transition-all">Logout</button>
              </>
            ) : (
              <Link href="/login" className="ml-1 px-5 py-1.5 rounded-xl text-sm font-bold text-white transition-all hover:-translate-y-0.5" style={{ background: 'linear-gradient(135deg, #0ea5e9, #6366f1)', boxShadow: '0 4px 16px rgba(14,165,233,0.3)' }}>Login</Link>
            )}
            <div className="ml-1"><ThemeToggle /></div>
          </nav>

          <div className="flex items-center gap-2 md:hidden">
            {isLoggedIn && <Link href="/profile"><div className="w-8 h-8 rounded-full bg-gradient-to-br from-sky-400 to-indigo-600 flex items-center justify-center"><User className="w-4 h-4 text-white" /></div></Link>}
            <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="p-1.5 rounded-xl hover:bg-sky-100/40 dark:hover:bg-sky-800/20 transition-colors" aria-label="Menu">
              {mobileMenuOpen ? <X className="w-5 h-5 text-sky-800 dark:text-sky-200" /> : <Menu className="w-5 h-5 text-sky-800 dark:text-sky-200" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Sidebar */}
      <div className={`md:hidden fixed inset-y-0 right-0 w-72 z-[60] flex flex-col transition-transform duration-500 ${mobileMenuOpen ? 'translate-x-0' : 'translate-x-full'}`}
        style={{ transitionTimingFunction: 'cubic-bezier(0.34,1.56,0.64,1)', backgroundColor: 'rgba(240,249,255,0.97)', backdropFilter: 'blur(32px)', boxShadow: '-8px 0 50px rgba(14,165,233,0.1)' }}>
        <div className="absolute inset-0 hidden dark:block" style={{ backgroundColor: 'rgba(2,6,23,0.97)' }} />
        <div className="relative flex items-center justify-between px-5 py-4 border-b border-sky-100/40 dark:border-sky-800/30">
          <h2 className="text-base font-black text-sky-900 dark:text-sky-100">Menu</h2>
          <button onClick={() => setMobileMenuOpen(false)} className="p-2 rounded-xl hover:bg-sky-100/50 dark:hover:bg-sky-800/30 transition-colors"><X className="w-5 h-5 text-sky-700 dark:text-sky-300" /></button>
        </div>
        <div className="relative flex-1 overflow-y-auto p-4 space-y-2">
          {isLoggedIn && user ? (
            <Link href="/profile" onClick={() => setMobileMenuOpen(false)} className="block">
              <div className="flex items-center gap-3 p-3 rounded-2xl border border-sky-200/40 dark:border-sky-700/20 hover:border-sky-300 dark:hover:border-sky-600 bg-white/30 dark:bg-sky-900/20 transition-all">
                <div className="w-11 h-11 rounded-full bg-gradient-to-br from-sky-400 to-indigo-600 flex items-center justify-center"><User className="w-5 h-5 text-white" /></div>
                <div><p className="font-bold text-sky-900 dark:text-sky-100 text-sm truncate">{user.fullName}</p><p className="text-xs text-sky-500/60 font-semibold flex items-center gap-1">Profil <ChevronRight className="w-3 h-3" /></p></div>
              </div>
            </Link>
          ) : (
            <Link href="/login" onClick={() => setMobileMenuOpen(false)} className="block p-3 rounded-2xl border border-dashed border-sky-200/40 dark:border-sky-700/20 text-center">
              <p className="text-xs text-sky-400/60 font-semibold">Login untuk mengakses fitur</p>
            </Link>
          )}
          <div className="border-t border-sky-100/30 dark:border-sky-800/20 my-2" />
          <div className="flex justify-center py-1"><ThemeToggle /></div>
          <div className="border-t border-sky-100/30 dark:border-sky-800/20 my-2" />
          {navItems.map((item) => (
            <Link key={item.label} href={item.href} onClick={() => setMobileMenuOpen(false)} className="block px-4 py-3 rounded-xl text-sm font-bold text-sky-800 dark:text-sky-200 hover:bg-sky-100/40 dark:hover:bg-sky-800/20 transition-colors">{item.label}</Link>
          ))}
          {isLoggedIn && (
            <button onClick={() => { logout(); setMobileMenuOpen(false); }} className="w-full flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-bold text-red-400 hover:bg-red-50/50 dark:hover:bg-red-900/10 transition-colors"><LogOut className="w-4 h-4" /> Logout</button>
          )}
        </div>
      </div>
      <div className={`md:hidden fixed inset-0 z-[55] transition-opacity duration-300 ${mobileMenuOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`} style={{ backgroundColor: 'rgba(2,6,23,0.2)' }} onClick={() => setMobileMenuOpen(false)} />
    </header>
  );
}
