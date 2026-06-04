'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  ClipboardList,
  BarChart3,
  LogOut,
  CreditCard,
  Home,
  ChevronRight,
  ChevronLeft,
  X,
} from 'lucide-react';

interface AdminSidebarProps {
  mobileOpen: boolean;
  onClose: () => void;
  onLogout: () => void;
  sidebarWidth: number;
  setSidebarWidth: (w: number) => void;
  isDragging: boolean;
  setIsDragging: (d: boolean) => void;
  activeTab?: string;
  setActiveTab?: (tab: 'overview' | 'eda' | 'predictions') => void;
}

const navItems = [
  { label: 'Ringkasan Utama', href: '/admin', icon: LayoutDashboard },
  { label: 'Riwayat Pengajuan', href: '/admin#predictions', icon: ClipboardList },
  { label: 'Analisis Dataset (EDA)', href: '/admin#eda', icon: BarChart3 },
];

export default function AdminSidebar({
  mobileOpen,
  onClose,
  onLogout,
  sidebarWidth,
  setSidebarWidth,
  isDragging,
  setIsDragging,
  activeTab,
  setActiveTab,
}: AdminSidebarProps) {
  const pathname = usePathname();
  const isCollapsed = sidebarWidth < 120;

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    const startX = e.clientX;
    const startWidth = sidebarWidth;
    let hasMoved = false;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = moveEvent.clientX - startX;
      if (Math.abs(deltaX) > 6) {
        hasMoved = true;
      }
      let newWidth = startWidth + deltaX;
      if (newWidth < 150) {
        newWidth = 72; // Snap to collapsed logo-only
      } else if (newWidth > 450) {
        newWidth = 450; // Dynamic resizing up to 450px wide
      }
      setSidebarWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      
      // If the drag movement was very minor, treat it as a click toggle!
      if (!hasMoved) {
        if (isCollapsed) {
          setSidebarWidth(260);
        } else {
          setSidebarWidth(72);
        }
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  const sidebarContent = (
    <div className="flex flex-col h-full overflow-hidden select-none">
      {/* Logo: Blue Card CreditCard exactly like homepage */}
      <div className={`py-5 border-b border-sky-100/30 dark:border-sky-800/20 transition-all ${isCollapsed ? 'px-2 flex justify-center' : 'px-5'}`}>
        <Link href="/admin" className={`flex items-center group ${isCollapsed ? 'justify-center' : 'gap-2.5'}`} title={isCollapsed ? "KreditinAja Admin" : undefined}>
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-400 to-indigo-600 flex items-center justify-center group-hover:scale-110 group-hover:rotate-3 transition-all duration-300" style={{ boxShadow: '0 4px 12px rgba(14,165,233,0.3)' }}>
            <CreditCard className="w-5 h-5 text-white" />
          </div>
          {!isCollapsed && (
            <div className="animate-fade-in">
              <span className="text-sm font-black text-sky-900 dark:text-sky-100" style={{ letterSpacing: '-0.03em' }}>
                Kreditin<span className="bg-gradient-to-r from-sky-400 to-indigo-600 bg-clip-text text-transparent ml-0.5">Aja!</span>
              </span>
              <p className="text-[9px] font-bold text-sky-400/50 uppercase tracking-wider">Admin Panel</p>
            </div>
          )}
        </Link>
      </div>

      {/* Nav Items with blue-indigo active styling */}
      <nav className={`flex-1 py-4 space-y-1 overflow-y-auto ${isCollapsed ? 'px-1.5' : 'px-3'}`}>
        {!isCollapsed && (
          <p className="px-3 mb-2 text-[9px] font-extrabold text-sky-400/50 uppercase tracking-[0.2em] animate-fade-in">Menu</p>
        )}
        {navItems.map((item) => {
          let isActive = false;
          if (activeTab) {
            if (item.href === '/admin') isActive = activeTab === 'overview';
            else if (item.href === '/admin#predictions') isActive = activeTab === 'predictions';
            else if (item.href === '/admin#eda') isActive = activeTab === 'eda';
            else if (item.href === '/admin#users') isActive = activeTab === 'eda';
          } else {
            isActive = pathname === item.href || (item.href === '/admin' && pathname === '/admin');
          }
          return (
            <Link
              key={item.label}
              href={item.href}
              onClick={(e) => {
                onClose();
                if (setActiveTab) {
                  if (item.href === '/admin') setActiveTab('overview');
                  else if (item.href === '/admin#predictions') setActiveTab('predictions');
                  else if (item.href === '/admin#eda') setActiveTab('eda');
                }
              }}
              title={isCollapsed ? item.label : undefined}
              className={`flex items-center rounded-xl text-sm font-semibold transition-all duration-200 group ${
                isCollapsed ? 'justify-center px-0 py-3' : 'gap-3 px-3 py-2.5'
              } ${isActive
                  ? 'bg-gradient-to-r from-sky-500/10 to-indigo-500/10 text-sky-600 dark:text-sky-400 border border-sky-200/30 dark:border-sky-700/20'
                  : 'text-sky-700/60 dark:text-sky-300/50 hover:bg-sky-50/50 dark:hover:bg-sky-800/20 hover:text-sky-800 dark:hover:text-sky-200'
                }`}
            >
              <item.icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-sky-500' : 'text-sky-400/60 group-hover:text-sky-500'}`} />
              {!isCollapsed && <span className="truncate">{item.label}</span>}
              {!isCollapsed && isActive && <ChevronRight className="w-3 h-3 ml-auto text-sky-400/60 flex-shrink-0" />}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className={`py-4 border-t border-sky-100/30 dark:border-sky-800/20 space-y-2 ${isCollapsed ? 'px-1.5' : 'px-3'}`}>
        <Link href="/" onClick={onClose} title={isCollapsed ? "Ke Halaman Utama" : undefined}
          className={`flex items-center rounded-xl text-sm font-semibold text-sky-700/50 dark:text-sky-300/40 hover:bg-sky-50/50 dark:hover:bg-sky-800/20 transition-all ${
            isCollapsed ? 'justify-center px-0 py-3' : 'gap-3 px-3 py-2.5'
          }`}>
          <Home className="w-4 h-4 flex-shrink-0" />
          {!isCollapsed && <span>Ke Halaman Utama</span>}
        </Link>
        <button onClick={onLogout} title={isCollapsed ? "Logout Admin" : undefined}
          className={`w-full flex items-center rounded-xl text-sm font-bold text-red-400 hover:bg-red-50/50 dark:hover:bg-red-900/10 transition-all ${
            isCollapsed ? 'justify-center px-0 py-3' : 'gap-3 px-3 py-2.5'
          }`}>
          <LogOut className="w-4 h-4 flex-shrink-0" />
          {!isCollapsed && <span>Logout Admin</span>}
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className="hidden lg:flex flex-col fixed left-0 top-0 bottom-0 z-40 glass-card-static border-r border-sky-100/30 dark:border-sky-800/20"
        style={{
          width: `${sidebarWidth}px`,
          boxShadow: '4px 0 30px rgba(14,165,233,0.04)',
          transition: isDragging ? 'none' : 'width 0.2s cubic-bezier(0.4, 0, 0.2, 1)'
        }}
      >
        {sidebarContent}

        {/* Drag handle line on the border */}
        <div
          onMouseDown={handleMouseDown}
          className="absolute right-0 top-0 bottom-0 w-[5px] cursor-col-resize hover:bg-sky-500/30 active:bg-sky-500/50 transition-colors z-50 group"
        >
          <div className="w-[1.5px] h-full mx-auto bg-transparent group-hover:bg-sky-400 group-active:bg-sky-500 transition-colors" />
        </div>

        {/* Tall Pill Toggle / Drag Handle Button */}
        <button
          onMouseDown={handleMouseDown}
          className="absolute top-1/2 -translate-y-1/2 -right-3.5 z-50 w-7 h-16 rounded-xl bg-white dark:bg-slate-800 border border-sky-100 dark:border-sky-800/80 shadow-lg flex flex-col items-center justify-center cursor-col-resize hover:scale-105 active:scale-95 text-sky-600 dark:text-sky-400 transition-all group"
          style={{ boxShadow: '4px 0 16px rgba(14,165,233,0.1)' }}
          title={isCollapsed ? "Tarik untuk memperlebar / Klik untuk expand" : "Tarik untuk mempersempit / Klik untuk collapse"}
        >
          {/* Subtle grab lines */}
          <div className="flex gap-0.5 mb-1.5 opacity-30 group-hover:opacity-85 transition-opacity">
            <div className="w-[1.5px] h-3 bg-sky-500 rounded-full" />
            <div className="w-[1.5px] h-3 bg-sky-500 rounded-full" />
          </div>
          {isCollapsed ? <ChevronRight className="w-3 h-3 text-sky-500" /> : <ChevronLeft className="w-3 h-3 text-sky-500" />}
        </button>
      </aside>

      {/* Mobile Overlay */}
      <div
        className={`lg:hidden fixed inset-0 z-[55] transition-opacity duration-300 ${mobileOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
        style={{ backgroundColor: 'rgba(2,6,23,0.3)' }}
        onClick={onClose}
      />

      {/* Mobile Sidebar */}
      <aside
        className={`lg:hidden fixed left-0 top-0 bottom-0 w-[280px] z-[60] flex flex-col transition-transform duration-500 glass-card-static ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}
        style={{ transitionTimingFunction: 'cubic-bezier(0.34,1.56,0.64,1)' }}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-sky-100/30 dark:border-sky-800/20">
          <span className="text-sm font-black text-sky-900 dark:text-sky-100">Menu Admin</span>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-sky-100/40 dark:hover:bg-sky-800/30 transition-colors">
            <X className="w-5 h-5 text-sky-700 dark:text-sky-300" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {sidebarContent}
        </div>
      </aside>
    </>
  );
}
