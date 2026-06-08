'use client';

import React, { useState, useEffect } from 'react';
import { Shield, Mail, Lock, ArrowRight, Eye, EyeOff, Home } from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

      <div className="relative z-10 flex items-center justify-center min-h-screen px-4 py-24">
        <div className="w-full max-w-2xl">
          
          <div className="overflow-hidden rounded-[28px] border border-violet-100/50 dark:border-violet-900/30 shadow-2xl shadow-violet-500/10">
            {/* Header Card (ss 1 style) */}
            <div className="bg-gradient-to-r from-violet-600 via-indigo-600 to-sky-600 px-10 py-12 text-center text-white relative">
              <div className="absolute top-0 right-0 w-24 h-24 bg-white/5 rounded-full -translate-y-6 translate-x-6 blur-xl" />
              <div className="absolute bottom-0 left-0 w-32 h-32 bg-white/5 rounded-full translate-y-12 -translate-x-12 blur-2xl" />
              
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-white/10 backdrop-blur-md border border-white/20 mb-5 shadow-inner">
                <Shield className="w-10 h-10 text-white" />
              </div>
              <h1 className="text-4xl font-extrabold tracking-tight mb-2.5">Admin Login 🔐</h1>
              <p className="text-violet-100 text-base font-medium max-w-md mx-auto">Masuk ke panel monitoring admin untuk memantau performa model MLOps</p>
            </div>

            {/* Body Card */}
            <div className="bg-white/95 dark:bg-slate-950/95 backdrop-blur-xl p-10 sm:p-12 space-y-8">
              {error && (
                <div className="px-5 py-4 rounded-2xl bg-rose-50 dark:bg-rose-950/20 border border-rose-200/50 dark:border-rose-800/30 text-rose-600 dark:text-rose-400 text-base font-semibold flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse" />
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2.5">
                  <label className="block text-sm font-bold uppercase tracking-wider text-violet-800 dark:text-violet-300">Email Admin</label>
                  <div className="relative">
                    <Mail className="absolute left-5 top-1/2 -translate-y-1/2 w-6 h-6 text-violet-400/60" />
                    <input 
                      type="email" 
                      value={form.email} 
                      onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))}
                      className="w-full pl-14 pr-5 py-5 text-lg rounded-[20px] bg-violet-50/40 dark:bg-violet-950/10 border border-violet-100 dark:border-violet-900/30 text-violet-900 dark:text-violet-100 font-medium placeholder:text-violet-400/30 focus:outline-none focus:ring-2 focus:ring-violet-500 transition-all" 
                      placeholder="admin@creditcare.id" 
                    />
                  </div>
                </div>

                <div className="space-y-2.5">
                  <label className="block text-sm font-bold uppercase tracking-wider text-violet-800 dark:text-violet-300">Kata Sandi</label>
                  <div className="relative">
                    <Lock className="absolute left-5 top-1/2 -translate-y-1/2 w-6 h-6 text-violet-400/60" />
                    <input 
                      type={showPw ? 'text' : 'password'} 
                      value={form.password} 
                      onChange={(e) => setForm(f => ({ ...f, password: e.target.value }))}
                      className="w-full pl-14 pr-14 py-5 text-lg rounded-[20px] bg-violet-50/40 dark:bg-violet-950/10 border border-violet-100 dark:border-violet-900/30 text-violet-900 dark:text-violet-100 font-medium placeholder:text-violet-400/30 focus:outline-none focus:ring-2 focus:ring-violet-500 transition-all" 
                      placeholder="Masukkan kata sandi admin" 
                    />
                    <button 
                      type="button" 
                      onClick={() => setShowPw(!showPw)} 
                      className="absolute right-5 top-1/2 -translate-y-1/2 text-violet-400/50 hover:text-violet-600 transition-colors"
                    >
                      {showPw ? <EyeOff className="w-6 h-6" /> : <Eye className="w-6 h-6" />}
                    </button>
                  </div>
                </div>

                <button 
                  type="submit" 
                  disabled={loading}
                  className="w-full group flex items-center justify-center gap-3 px-6 py-5 rounded-2xl text-white font-black text-lg transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-violet-500/20 active:translate-y-0 disabled:opacity-50 mt-6 cursor-pointer"
                  style={{ background: 'linear-gradient(135deg, #8b5cf6, #6366f1)' }}
                >
                  {loading ? (
                    <div className="w-7 h-7 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>Masuk ke Panel Admin <ArrowRight className="w-6 h-6 group-hover:translate-x-1.5 transition-transform" /></>
                  )}
                </button>
              </form>

              {/* Informative info box (ss 1 style) */}
              <div className="bg-violet-50/80 dark:bg-violet-950/20 border border-violet-100 dark:border-violet-900/30 text-violet-800 dark:text-violet-300 rounded-2xl p-5 text-base font-medium leading-relaxed flex items-start gap-4">
                <span className="text-xl leading-none mt-0.5">🔑</span>
                <div>
                  Akses Terbatas: Halaman ini dikhususkan bagi administrator sistem. Setiap upaya masuk akan dicatat secara otomatis dalam audit log.
                </div>
              </div>

              {/* Action Links */}
              <div className="flex items-center justify-center pt-5 border-t border-violet-100/30 dark:border-violet-900/20">
                <Link 
                  href="/" 
                  className="flex items-center gap-2 text-base font-bold text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
                >
                  <Home className="w-5 h-5" /> Lihat-lihat Dulu
                </Link>
              </div>

            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
