'use client';

import React, { useState, useMemo } from 'react';
import { Search, ChevronLeft, ChevronRight, ChevronDown, ChevronUp } from 'lucide-react';

interface Column {
  key: string;
  label: string;
  sortable?: boolean;
  render?: (value: unknown, row: Record<string, unknown>) => React.ReactNode;
}

interface DataTableProps {
  columns: Column[];
  data: Record<string, unknown>[];
  pageSize?: number;
  searchKeys?: string[];
  title?: string;
  emptyMessage?: string;
}

export default function DataTable({
  columns,
  data,
  pageSize = 10,
  searchKeys = [],
  title,
  emptyMessage = 'Belum ada data',
}: DataTableProps) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState('');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const filtered = useMemo(() => {
    let result = [...data];
    if (search && searchKeys.length > 0) {
      const q = search.toLowerCase();
      result = result.filter(row =>
        searchKeys.some(k => String(row[k] || '').toLowerCase().includes(q))
      );
    }
    if (sortKey) {
      result.sort((a, b) => {
        const va = a[sortKey], vb = b[sortKey];
        const cmp = String(va || '').localeCompare(String(vb || ''), undefined, { numeric: true });
        return sortDir === 'asc' ? cmp : -cmp;
      });
    }
    return result;
  }, [data, search, searchKeys, sortKey, sortDir]);

  const totalPages = Math.ceil(filtered.length / pageSize);
  const pageData = filtered.slice(page * pageSize, (page + 1) * pageSize);

  const handleSort = (key: string) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  };

  return (
    <div className="glass-card-static rounded-2xl overflow-hidden" style={{ boxShadow: '0 4px 20px rgba(14,165,233,0.06)' }}>
      {/* Header */}
      <div className="px-5 py-4 border-b border-sky-100/30 dark:border-sky-800/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        {title && <h4 className="text-sm font-black text-sky-950 dark:text-sky-50">{title}</h4>}
        <div className="relative w-full sm:w-60">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-sky-400/50" />
          <input
            type="text" value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            className="w-full pl-9 pr-3 py-2.5 rounded-lg bg-sky-50/60 dark:bg-sky-900/20 border border-sky-200/30 dark:border-sky-700/20 text-xs font-semibold text-sky-900 dark:text-sky-100 placeholder:text-sky-400/40 transition-all"
            placeholder="Cari..."
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs md:text-sm">
          <thead>
            <tr className="border-b border-sky-100/30 dark:border-sky-800/20">
              {columns.map(col => (
                <th key={col.key} className="px-4 py-3.5 text-left font-black text-sky-600 dark:text-sky-400 uppercase tracking-wider text-[11px] md:text-xs">
                  {col.sortable ? (
                    <button onClick={() => handleSort(col.key)} className="flex items-center gap-1 hover:text-sky-800 dark:hover:text-sky-200 transition-colors">
                      {col.label}
                      {sortKey === col.key ? (sortDir === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />) : <ChevronDown className="w-3 h-3 opacity-30" />}
                    </button>
                  ) : col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageData.length === 0 ? (
              <tr><td colSpan={columns.length} className="px-4 py-12 text-center text-sky-400/50 font-semibold">{emptyMessage}</td></tr>
            ) : (
              pageData.map((row, ri) => (
                <tr key={ri} className="border-b border-sky-50/30 dark:border-sky-800/10 hover:bg-sky-50/30 dark:hover:bg-sky-900/10 transition-colors">
                  {columns.map(col => (
                    <td key={col.key} className="px-4 py-4 font-bold text-sky-900 dark:text-sky-100 whitespace-nowrap">
                      {col.render ? col.render(row[col.key], row) : String(row[col.key] ?? '')}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-5 py-3 border-t border-sky-100/30 dark:border-sky-800/20 flex items-center justify-between">
          <span className="text-[10px] font-bold text-sky-400/60">
            {filtered.length} data · Halaman {page + 1}/{totalPages}
          </span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
              className="p-1.5 rounded-lg hover:bg-sky-100/40 dark:hover:bg-sky-800/20 disabled:opacity-30 transition-colors">
              <ChevronLeft className="w-3.5 h-3.5 text-sky-600 dark:text-sky-400" />
            </button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const pg = Math.max(0, Math.min(page - 2, totalPages - 5)) + i;
              if (pg >= totalPages) return null;
              return (
                <button key={pg} onClick={() => setPage(pg)}
                  className={`w-7 h-7 rounded-lg text-[10px] font-bold transition-all ${pg === page ? 'bg-gradient-to-r from-sky-500 to-indigo-600 text-white shadow-sm' : 'text-sky-600/60 dark:text-sky-400/50 hover:bg-sky-100/40 dark:hover:bg-sky-800/20'}`}>
                  {pg + 1}
                </button>
              );
            })}
            <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
              className="p-1.5 rounded-lg hover:bg-sky-100/40 dark:hover:bg-sky-800/20 disabled:opacity-30 transition-colors">
              <ChevronRight className="w-3.5 h-3.5 text-sky-600 dark:text-sky-400" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
