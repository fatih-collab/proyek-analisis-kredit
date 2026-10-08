'use client';

import React, { useState, useEffect } from 'react';
import { User, Save, Check, ArrowRight, Briefcase, DollarSign, MapPin, GraduationCap, Users, Heart, Phone, Mail, Sparkles, CheckCircle2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';

export default function ProfilePage() {
  const { user, isLoggedIn, isLoading, updateProfile } = useAuth();
  const router = useRouter();
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState({ fullName: '', email: '', phone: '', age: '', gender: '', maritalStatus: '', dependents: '', education: '', employment: '', monthlyIncome: '', additionalIncome: '', address: '', existingInstallments: '' });

  useEffect(() => {
    if (!isLoading && !isLoggedIn) { router.push('/login'); return; }
    if (user?.profile) setForm({ fullName: user.profile.fullName || '', email: user.profile.email || '', phone: user.profile.phone || '', age: user.profile.age || '', gender: user.profile.gender || '', maritalStatus: user.profile.maritalStatus || '', dependents: user.profile.dependents || '', education: user.profile.education || '', employment: user.profile.employment || '', monthlyIncome: user.profile.monthlyIncome || '', additionalIncome: user.profile.additionalIncome || '', address: user.profile.address || '', existingInstallments: user.profile.existingInstallments || '0' });
  }, [user, isLoggedIn, isLoading, router]);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    const req = ['fullName', 'phone', 'age', 'gender', 'maritalStatus', 'education', 'employment', 'monthlyIncome', 'existingInstallments'];
    const done = req.every(k => form[k as keyof typeof form]?.trim());
    updateProfile({ ...form, profileCompleted: done });
    setSaved(true); setTimeout(() => setSaved(false), 2000);
    if (done && !user?.profile.profileCompleted) setTimeout(() => router.push('/predict'), 1500);
  };

  if (isLoading) return <div className="min-h-screen flex items-center justify-center"><div className="w-10 h-10 border-3 border-sky-200 border-t-sky-500 rounded-full animate-spin-slow" /></div>;

  const filledCount = ['fullName', 'phone', 'age', 'gender', 'maritalStatus', 'education', 'employment', 'monthlyIncome', 'existingInstallments'].filter(k => form[k as keyof typeof form]?.trim()).length;
  const progress = Math.round((filledCount / 9) * 100);

  const fields = [
    { key: 'fullName', label: 'Nama Lengkap', icon: User, type: 'text', ph: 'Nama sesuai KTP', req: true },
    { key: 'email', label: 'Email', icon: Mail, type: 'email', ph: 'Email', req: false, disabled: true },
    { key: 'phone', label: 'No. Telepon', icon: Phone, type: 'tel', ph: '08xxxxxxxxxx', req: true },
    { key: 'age', label: 'Usia', icon: User, type: 'number', ph: 'Usia dalam tahun', req: true },
    { key: 'gender', label: 'Jenis Kelamin', icon: Users, type: 'select', options: ['', 'Laki-laki', 'Perempuan'], req: true },
    { key: 'maritalStatus', label: 'Status Pernikahan', icon: Heart, type: 'select', options: ['', 'Belum Menikah', 'Menikah', 'Cerai'], req: true },
    { key: 'dependents', label: 'Jumlah Tanggungan', icon: Users, type: 'number', ph: '0', req: false },
    { key: 'education', label: 'Pendidikan Terakhir', icon: GraduationCap, type: 'select', options: ['', 'SD', 'SMP', 'SMA/SMK', 'D3', 'S1', 'S2', 'S3'], req: true },
    { key: 'employment', label: 'Status Pekerjaan', icon: Briefcase, type: 'select', options: ['', 'PNS', 'Karyawan Swasta', 'Wiraswasta', 'Freelancer', 'Mahasiswa', 'Tidak Bekerja'], req: true },
    { key: 'monthlyIncome', label: 'Pendapatan Bulanan ($)', icon: DollarSign, type: 'number', ph: 'Contoh: 5000', req: true },
    { key: 'additionalIncome', label: 'Pendapatan Tambahan ($)', icon: DollarSign, type: 'number', ph: 'Opsional, contoh: 500', req: false },
    { key: 'existingInstallments', label: 'Cicilan Bulanan Aktif di Tempat Lain ($)', icon: DollarSign, type: 'number', ph: 'Contoh: 200 (isi 0 jika tidak ada cicilan aktif)', req: true },
    { key: 'address', label: 'Alamat', icon: MapPin, type: 'textarea', ph: 'Alamat lengkap', req: false },
  ];

  return (
    <div className="min-h-screen relative transition-colors duration-300 noise-overlay">
      <div className="gradient-mesh" /><div className="orb orb-1" /><div className="orb orb-2" />
      <Header />
      <div className="relative z-10 max-w-2xl mx-auto px-4 pt-28 pb-16">
        <div className="text-center mb-6">

          <h1 className="text-2xl md:text-3xl font-black text-sky-950 dark:text-sky-100 mb-2" style={{ letterSpacing: '-0.03em' }}>Profil Saya</h1>
          <p className="text-sky-700/50 dark:text-sky-300/40 text-sm">Lengkapi data untuk menggunakan fitur prediksi</p>
        </div>

        {/* Progress bar */}
        <div className="glass-card-static rounded-2xl px-5 py-4 mb-6" style={{ boxShadow: '0 4px 20px rgba(14,165,233,0.06)' }}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-sky-700 dark:text-sky-300">Kelengkapan Profil</span>
            <span className={`text-xs font-extrabold ${progress === 100 ? 'text-emerald-500' : 'text-sky-500'}`}>{progress}%</span>
          </div>
          <div className="w-full h-2.5 rounded-full bg-sky-100/60 dark:bg-sky-800/20 overflow-hidden">
            <div className="h-full rounded-full transition-all duration-700 ease-out" style={{ width: `${progress}%`, background: progress === 100 ? 'linear-gradient(90deg, #10b981, #059669)' : 'linear-gradient(90deg, #0ea5e9, #6366f1)' }} />
          </div>
          {progress === 100 && (
            <div className="flex items-center gap-1.5 mt-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              <span className="text-[11px] font-bold text-emerald-500">Profil lengkap! Anda bisa menggunakan fitur prediksi.</span>
            </div>
          )}
        </div>

        {/* Form */}
        <div className="glass-card-static rounded-3xl overflow-hidden" style={{ boxShadow: '0 8px 40px rgba(14,165,233,0.06)' }}>
          <div className="px-6 py-6">
            <form onSubmit={handleSave} className="space-y-4">
              {fields.map((f) => (
                <div key={f.key}>
                  <label className="block text-xs font-bold text-sky-700 dark:text-sky-300 mb-1.5">{f.label} {f.req && <span className="text-red-400">*</span>}</label>
                  <div className="relative">
                    <f.icon className="absolute left-3 top-3.5 w-4 h-4 text-sky-400/60" />
                    {f.type === 'select' ? (
                      <select value={form[f.key as keyof typeof form]} onChange={(e) => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                        className="w-full pl-10 pr-4 py-3 rounded-xl bg-sky-50/60 dark:bg-sky-900/20 border border-sky-200/40 dark:border-sky-700/30 text-sky-900 dark:text-sky-100 text-sm font-medium transition-all appearance-none">
                        {f.options?.map(o => <option key={o} value={o}>{o || `Pilih ${f.label}`}</option>)}
                      </select>
                    ) : f.type === 'textarea' ? (
                      <textarea value={form[f.key as keyof typeof form]} onChange={(e) => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                        className="w-full pl-10 pr-4 py-3 rounded-xl bg-sky-50/60 dark:bg-sky-900/20 border border-sky-200/40 dark:border-sky-700/30 text-sky-900 dark:text-sky-100 text-sm font-medium placeholder:text-sky-400/40 transition-all resize-none" placeholder={f.ph} rows={3} />
                    ) : (
                      <input type={f.type} value={form[f.key as keyof typeof form]} onChange={(e) => setForm(prev => ({ ...prev, [f.key]: e.target.value }))} disabled={f.disabled}
                        className="w-full pl-10 pr-4 py-3 rounded-xl bg-sky-50/60 dark:bg-sky-900/20 border border-sky-200/40 dark:border-sky-700/30 text-sky-900 dark:text-sky-100 text-sm font-medium placeholder:text-sky-400/40 transition-all disabled:opacity-50" placeholder={f.ph} />
                    )}
                  </div>
                </div>
              ))}
              <button type="submit"
                className="w-full group flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl text-white font-bold text-sm transition-all duration-300 hover:-translate-y-0.5 mt-4"
                style={{ background: saved ? 'linear-gradient(135deg, #10b981, #059669)' : 'linear-gradient(135deg, #0ea5e9, #6366f1)', boxShadow: '0 6px 24px rgba(14,165,233,0.3)' }}>
                {saved ? <><Check className="w-4 h-4" /> Tersimpan!</> : <><Save className="w-4 h-4" /> Simpan Profil</>}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
