'use client';

import React, { useState, useEffect } from 'react';
import { Shield, Mail, Lock, ArrowRight, Eye, EyeOff } from 'lucide-react';
import { useRouter } from 'next/navigation';

const BACKEND_URL = 'http://localhost:8000';

export default function AdminLoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: '', password: '' });
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const session = localStorage.getItem('mlops_admin_session');
    if (session) {
      router.push('/admin');
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.email || !form.password) {
      setError('Email dan password wajib diisi');
      return;
    }
    setLoading(true);

    try {
      const res = await fetch(`${BACKEND_URL}/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const data = await res.json();

      if (data.success && data.token) {
        localStorage.setItem('mlops_admin_session', JSON.stringify({
          email: form.email,
          loginAt: new Date().toISOString(),
          token: data.token,
        }));
        router.push('/admin');
      } else {
        setError(data.error || 'Email atau password admin salah');
      }
    } catch {
      setError('Gagal terhubung ke server backend');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen relative transition-colors duration-300 noise-overlay">
      <div className="gradient-mesh" /><div className="orb orb-1" /><div className="orb orb-2" />

      {/* No Header — admin login is secret */}

      <div className="relative z-10 flex items-center justify-center min-h-screen px-4 py-24">
        <div className="w-full max-w-md">
          <div className="text-center mb-6">

            <h1 className="text-2xl font-black text-sky-950 dark:text-sky-100" style={{ letterSpacing: '-0.03em' }}>Admin Login 🔐</h1>
            <p className="text-sm text-sky-700/50 dark:text-sky-300/40 mt-1">Masuk ke panel monitoring admin</p>
          </div>

          <div className="gradient-border" style={{ background: 'linear-gradient(135deg, #0ea5e9, #6366f1, #8b5cf6, #0ea5e9)', backgroundSize: '300% 300%', animation: 'gradientShift 4s ease infinite' }}>
            <div className="glass-card-static rounded-[22px] p-6">
              <form onSubmit={handleSubmit} className="space-y-4">
                {error && <div className="px-4 py-3 rounded-xl bg-red-50/80 dark:bg-red-900/20 border border-red-200/50 dark:border-red-800/30 text-red-500 text-sm font-medium">{error}</div>}
                <div>
                  <label className="block text-xs font-bold text-sky-700 dark:text-sky-300 mb-1.5">Email Admin</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-sky-400/60" />
                    <input type="email" value={form.email} onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))}
                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-sky-50/60 dark:bg-sky-900/20 border border-sky-200/40 dark:border-sky-700/30 text-sky-900 dark:text-sky-100 text-sm font-medium placeholder:text-sky-400/40 transition-all" placeholder="admin@kreditinaja.id" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-sky-700 dark:text-sky-300 mb-1.5">Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-sky-400/60" />
                    <input type={showPw ? 'text' : 'password'} value={form.password} onChange={(e) => setForm(f => ({ ...f, password: e.target.value }))}
                      className="w-full pl-10 pr-12 py-3 rounded-xl bg-sky-50/60 dark:bg-sky-900/20 border border-sky-200/40 dark:border-sky-700/30 text-sky-900 dark:text-sky-100 text-sm font-medium placeholder:text-sky-400/40 transition-all" placeholder="Masukkan password admin" />
                    <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-sky-400/50 hover:text-sky-600 transition-colors">
                      {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <button type="submit" disabled={loading}
                  className="w-full group flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl text-white font-bold text-sm transition-all duration-300 hover:-translate-y-0.5 disabled:opacity-50 mt-2"
                  style={{ background: 'linear-gradient(135deg, #0ea5e9, #6366f1)', boxShadow: '0 6px 24px rgba(14,165,233,0.3)' }}>
                  {loading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin-slow" /> : <><Lock className="w-4 h-4" /> Login Admin <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" /></>}
                </button>
              </form>

              <div className="mt-5 pt-4 border-t border-sky-100/30 dark:border-sky-800/20">
                <p className="text-[11px] text-sky-500/40 text-center font-medium">
                  Panel ini hanya untuk administrator sistem
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
