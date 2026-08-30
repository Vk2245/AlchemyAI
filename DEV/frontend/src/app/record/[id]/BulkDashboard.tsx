"use client";

import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import {
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  XCircle,
  Package,
  TrendingUp,
  AlertTriangle,
  Layers,
} from "lucide-react";

// Premium color palette for charts
const CHART_COLORS = [
  "#6366f1", "#8b5cf6", "#a78bfa", "#c084fc",
  "#34d399", "#2dd4bf", "#22d3ee", "#38bdf8",
  "#f472b6", "#fb923c", "#fbbf24", "#a3e635",
];

interface BulkDashboardProps {
  recordData: {
    categories?: Record<string, any[]>;
    stats?: {
      total: number;
      success: number;
      failed: number;
      success_rate: number;
      category_distribution: Record<string, number>;
    };
    excel_path?: string;
  };
}

export default function BulkDashboard({ recordData }: BulkDashboardProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedItem, setExpandedItem] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 15;

  const categories = recordData.categories || {};
  const stats = recordData.stats || {
    total: 0,
    success: 0,
    failed: 0,
    success_rate: 0,
    category_distribution: {},
  };

  // Compute stats from categories if stats are not available (old records)
  const computedStats = useMemo(() => {
    if (stats.total > 0) return stats;
    let total = 0;
    let failed = 0;
    const dist: Record<string, number> = {};
    Object.entries(categories).forEach(([cat, items]) => {
      total += items.length;
      dist[cat] = items.length;
      if (cat === "Failed") failed += items.length;
    });
    return {
      total,
      success: total - failed,
      failed,
      success_rate: total > 0 ? Math.round(((total - failed) / total) * 100 * 10) / 10 : 0,
      category_distribution: dist,
    };
  }, [stats, categories]);

  // Chart data for category distribution (exclude "Failed")
  const categoryChartData = useMemo(() => {
    return Object.entries(computedStats.category_distribution)
      .filter(([cat]) => cat !== "Failed")
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([name, count]) => ({ name: name.length > 18 ? name.slice(0, 16) + "…" : name, fullName: name, count }));
  }, [computedStats]);

  // Pie data for success vs failure
  const successPieData = useMemo(() => [
    { name: "Enriched", value: computedStats.success, color: "#34d399" },
    { name: "Failed", value: computedStats.failed, color: "#f87171" },
  ], [computedStats]);

  // Filtered items for the data explorer
  const filteredItems = useMemo(() => {
    let items: any[] = [];
    if (selectedCategory === "all") {
      Object.values(categories).forEach((catItems) => {
        items = items.concat(catItems);
      });
    } else {
      items = categories[selectedCategory] || [];
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      items = items.filter((item) => {
        const desc = (item["INPUT - Part_Desc"] || "").toLowerCase();
        const cat = (item["Category"] || "").toLowerCase();
        return desc.includes(q) || cat.includes(q);
      });
    }

    return items;
  }, [categories, selectedCategory, searchQuery]);

  const totalPages = Math.ceil(filteredItems.length / ITEMS_PER_PAGE);
  const paginatedItems = filteredItems.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  // Get important keys for each item (excluding INPUT and Category and Error)
  const getItemKeys = (item: any) => {
    return Object.keys(item).filter(
      (k) => !["INPUT - Part_Desc", "Category", "Error"].includes(k) && item[k] !== "" && item[k] !== null && item[k] !== undefined
    );
  };

  const categoryNames = Object.keys(categories);

  return (
    <div className="space-y-6">
      {/* Stats Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-panel rounded-2xl p-5 relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-20 h-20 bg-indigo-500/10 rounded-full blur-3xl -mr-6 -mt-6" />
          <Package size={16} className="text-indigo-400 mb-2" />
          <p className="text-xs text-[var(--muted)] uppercase tracking-wider mb-1">Total Items</p>
          <p className="text-3xl font-extrabold text-[var(--foreground)]">{computedStats.total.toLocaleString()}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="glass-panel rounded-2xl p-5 relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-500/10 rounded-full blur-3xl -mr-6 -mt-6" />
          <CheckCircle2 size={16} className="text-emerald-400 mb-2" />
          <p className="text-xs text-[var(--muted)] uppercase tracking-wider mb-1">Enriched</p>
          <p className="text-3xl font-extrabold text-emerald-400">{computedStats.success.toLocaleString()}</p>
          <p className="text-xs text-[var(--muted)] mt-1">{computedStats.success_rate}% success</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-panel rounded-2xl p-5 relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-20 h-20 bg-red-500/10 rounded-full blur-3xl -mr-6 -mt-6" />
          <AlertTriangle size={16} className="text-red-400 mb-2" />
          <p className="text-xs text-[var(--muted)] uppercase tracking-wider mb-1">Failed</p>
          <p className="text-3xl font-extrabold text-red-400">{computedStats.failed.toLocaleString()}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="glass-panel rounded-2xl p-5 relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-20 h-20 bg-purple-500/10 rounded-full blur-3xl -mr-6 -mt-6" />
          <Layers size={16} className="text-purple-400 mb-2" />
          <p className="text-xs text-[var(--muted)] uppercase tracking-wider mb-1">Categories</p>
          <p className="text-3xl font-extrabold text-[var(--foreground)]">
            {categoryNames.filter((c) => c !== "Failed").length}
          </p>
        </motion.div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Category Distribution Bar Chart */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="lg:col-span-2 glass-panel-strong rounded-2xl p-6"
        >
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-4 flex items-center gap-2">
            <TrendingUp size={16} className="text-indigo-400" />
            Category Distribution
          </h3>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryChartData} margin={{ top: 5, right: 20, left: 0, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 10 }}
                  angle={-35}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    background: "rgba(15,15,25,0.95)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "12px",
                    color: "#fff",
                    fontSize: "12px",
                  }}
                  formatter={(value: any, _name: any, props: any) => [
                    `${value} items`,
                    props.payload.fullName,
                  ]}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {categoryChartData.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Success/Failure Pie Chart */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="glass-panel-strong rounded-2xl p-6"
        >
          <h3 className="text-sm font-semibold text-[var(--foreground)] mb-4 flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-400" />
            Extraction Rate
          </h3>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={successPieData}
                  cx="50%"
                  cy="45%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="value"
                  strokeWidth={0}
                >
                  {successPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Legend
                  verticalAlign="bottom"
                  formatter={(value: string) => (
                    <span style={{ color: "rgba(255,255,255,0.7)", fontSize: "12px" }}>{value}</span>
                  )}
                />
                <Tooltip
                  contentStyle={{
                    background: "rgba(15,15,25,0.95)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "12px",
                    color: "#fff",
                    fontSize: "12px",
                  }}
                  formatter={(value: any) => [`${value} items`]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="text-center -mt-2">
            <p className="text-2xl font-bold text-[var(--foreground)]">{computedStats.success_rate}%</p>
            <p className="text-xs text-[var(--muted)]">Success Rate</p>
          </div>
        </motion.div>
      </div>

      {/* Data Explorer */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="glass-panel-strong rounded-2xl p-6"
      >
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
          <h3 className="text-sm font-semibold text-[var(--foreground)] flex items-center gap-2">
            <Filter size={16} className="text-blue-400" />
            Data Explorer
            <span className="text-xs text-[var(--muted)] font-normal ml-2">
              ({filteredItems.length} items)
            </span>
          </h3>

          <div className="flex gap-3 w-full md:w-auto">
            {/* Search */}
            <div className="relative flex-1 md:w-56">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
              <input
                type="text"
                placeholder="Search items..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full pl-9 pr-3 py-2 bg-white/[0.03] border border-[var(--border)] rounded-xl text-xs text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:border-indigo-500/50 transition-colors"
              />
            </div>

            {/* Category Filter */}
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 bg-white/[0.03] border border-[var(--border)] rounded-xl text-xs text-[var(--foreground)] focus:outline-none focus:border-indigo-500/50 transition-colors appearance-none cursor-pointer"
            >
              <option value="all" className="bg-[#0f111a] text-white">All Categories</option>
              {categoryNames
                .sort((a, b) => (categories[b]?.length || 0) - (categories[a]?.length || 0))
                .map((cat) => (
                  <option key={cat} value={cat} className="bg-[#0f111a] text-white">
                    {cat} ({categories[cat]?.length || 0})
                  </option>
                ))}
            </select>
          </div>
        </div>

        {/* Items Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-white/10">
                <th className="pb-3 text-xs font-semibold text-[var(--muted)] uppercase tracking-wider w-8">#</th>
                <th className="pb-3 text-xs font-semibold text-[var(--muted)] uppercase tracking-wider">Input Description</th>
                <th className="pb-3 text-xs font-semibold text-[var(--muted)] uppercase tracking-wider">Category</th>
                <th className="pb-3 text-xs font-semibold text-[var(--muted)] uppercase tracking-wider">Status</th>
                <th className="pb-3 text-xs font-semibold text-[var(--muted)] uppercase tracking-wider text-right">Fields</th>
              </tr>
            </thead>
            <tbody>
              {paginatedItems.map((item, i) => {
                const globalIdx = (currentPage - 1) * ITEMS_PER_PAGE + i;
                const isFailed = item.Category === "Failed" || !!item.Error;
                const keys = getItemKeys(item);
                const isExpanded = expandedItem === globalIdx;

                return (
                  <React.Fragment key={globalIdx}>
                    <tr
                      className="border-b border-white/5 hover:bg-white/[0.02] cursor-pointer transition-colors"
                      onClick={() => setExpandedItem(isExpanded ? null : globalIdx)}
                    >
                      <td className="py-3 text-xs text-[var(--muted)]">{globalIdx + 1}</td>
                      <td className="py-3 text-xs text-[var(--foreground)] max-w-[300px] truncate font-mono">
                        {item["INPUT - Part_Desc"] || "—"}
                      </td>
                      <td className="py-3">
                        <span
                          className={`text-xs px-2.5 py-1 rounded-lg font-medium ${
                            isFailed
                              ? "bg-red-500/10 text-red-400 border border-red-500/20"
                              : "bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                          }`}
                        >
                          {item.Category || "—"}
                        </span>
                      </td>
                      <td className="py-3">
                        {isFailed ? (
                          <XCircle size={14} className="text-red-400" />
                        ) : (
                          <CheckCircle2 size={14} className="text-emerald-400" />
                        )}
                      </td>
                      <td className="py-3 text-xs text-[var(--muted)] text-right flex items-center justify-end gap-1">
                        {keys.length}
                        {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </td>
                    </tr>

                    {/* Expanded Details */}
                    <AnimatePresence>
                      {isExpanded && (
                        <tr>
                          <td colSpan={5} className="p-0">
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{ duration: 0.2 }}
                              className="overflow-hidden"
                            >
                              <div className="px-6 py-4 bg-white/[0.02] border-b border-white/5">
                                {isFailed && item.Error && (
                                  <p className="text-xs text-red-400 mb-3 flex items-center gap-2">
                                    <AlertTriangle size={12} />
                                    Error: {item.Error}
                                  </p>
                                )}
                                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                                  {keys.map((key) => (
                                    <div key={key} className="bg-white/[0.03] rounded-lg p-2.5 border border-white/5">
                                      <p className="text-[10px] text-[var(--muted)] uppercase tracking-wider mb-0.5">
                                        {key}
                                      </p>
                                      <p className="text-xs text-[var(--foreground)] font-medium truncate">
                                        {String(item[key])}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </motion.div>
                          </td>
                        </tr>
                      )}
                    </AnimatePresence>
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/5">
            <p className="text-xs text-[var(--muted)]">
              Page {currentPage} of {totalPages}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1.5 text-xs rounded-lg border border-[var(--border)] text-[var(--secondary)] hover:text-[var(--foreground)] hover:border-indigo-500/50 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              {/* Page numbers */}
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum: number;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (currentPage <= 3) {
                  pageNum = i + 1;
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = currentPage - 2 + i;
                }
                return (
                  <button
                    key={pageNum}
                    onClick={() => setCurrentPage(pageNum)}
                    className={`w-8 h-8 text-xs rounded-lg transition-all ${
                      currentPage === pageNum
                        ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                        : "border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)]"
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1.5 text-xs rounded-lg border border-[var(--border)] text-[var(--secondary)] hover:text-[var(--foreground)] hover:border-indigo-500/50 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
