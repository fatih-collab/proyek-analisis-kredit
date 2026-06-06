'use client';

import React from 'react';
import { Shield, Cpu, BarChart3, ExternalLink, Mail } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="relative py-12 px-4 md:px-6 border-t border-sky-100/50 dark:border-sky-800/30">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          <div>
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center">
                <Cpu className="w-5 h-5 text-white" />
              </div>
              <span className="text-base font-extrabold text-sky-900 dark:text-sky-100" style={{ letterSpacing: '-0.02em' }}>
                KreditinAja!
              </span>
            </div>
            <p className="text-sm text-sky-700/60 dark:text-sky-300/50 leading-relaxed max-w-xs">
              Platform analisis risiko dan deteksi kelayakan nasabah pinjaman berbasis MLOps dengan algoritma Gradient Boosting.
            </p>
          </div>
          <div>
            <h4 className="text-sm font-bold text-sky-900 dark:text-sky-100 mb-3">Platform</h4>
            <div className="space-y-2">
              {[
                { label: 'Beranda', href: '/' },
                { label: 'Prediksi', href: '/predict' },
                { label: 'Dashboard', href: '/dashboard' },
                { label: 'Profil', href: '/profile' },
              ].map((link) => (
                <a key={link.label} href={link.href} className="block text-sm text-sky-700/60 dark:text-sky-300/50 hover:text-sky-600 dark:hover:text-sky-300 transition-colors">
                  {link.label}
                </a>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-sm font-bold text-sky-900 dark:text-sky-100 mb-3">Teknologi</h4>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-sky-700/60 dark:text-sky-300/50">
                <BarChart3 className="w-4 h-4" /> Gradient Boosting Algorithm
              </div>
              <div className="flex items-center gap-2 text-sm text-sky-700/60 dark:text-sky-300/50">
                <ExternalLink className="w-4 h-4" /> MLOps Pipeline
              </div>
              <div className="flex items-center gap-2 text-sm text-sky-700/60 dark:text-sky-300/50">
                <Shield className="w-4 h-4" /> Data Encrypted & Secure
              </div>
            </div>
          </div>
        </div>
        <div className="pt-6 border-t border-sky-100/50 dark:border-sky-800/30 flex flex-col md:flex-row items-center justify-between gap-3">
          <p className="text-xs text-sky-500/60 dark:text-sky-400/50">
            © {new Date().getFullYear()} KreditinAja! — MLOps Gradient Boosting.
          </p>
          <div className="flex items-center gap-4">
            <a href="https://github.com" target="_blank" rel="noopener" className="text-sky-500/50 hover:text-sky-600 transition-colors"><ExternalLink className="w-4 h-4" /></a>
            <a href="mailto:info@kreditinaja.id" className="text-sky-500/50 hover:text-sky-600 transition-colors"><Mail className="w-4 h-4" /></a>
          </div>
        </div>
      </div>
    </footer>
  );
}
