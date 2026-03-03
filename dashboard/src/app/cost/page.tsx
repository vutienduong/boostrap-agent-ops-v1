"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { fetchCostMetrics, CostMetrics } from "@/lib/api";

const PROJECT_ID = "01JDEFAULTPROJECT000000";

export default function CostPage() {
  const [metrics, setMetrics] = useState<CostMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCostMetrics(PROJECT_ID)
      .then(setMetrics)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="max-w-6xl mx-auto p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Cost Analytics</h1>
        <p className="text-sm text-gray-500 mt-1">Token usage and cost across all runs</p>
      </div>

      {loading && <p className="text-gray-500">Loading...</p>}

      {metrics && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="bg-white rounded-lg border p-4">
              <p className="text-sm text-gray-500">Total Cost</p>
              <p className="text-2xl font-bold mt-1">${metrics.total_cost_usd.toFixed(4)}</p>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <p className="text-sm text-gray-500">Prompt Tokens</p>
              <p className="text-2xl font-bold mt-1">{metrics.total_prompt_tokens.toLocaleString()}</p>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <p className="text-sm text-gray-500">Completion Tokens</p>
              <p className="text-2xl font-bold mt-1">{metrics.total_completion_tokens.toLocaleString()}</p>
            </div>
          </div>

          {/* Cost by day chart */}
          {metrics.by_day.length > 0 && (
            <div className="bg-white rounded-lg border p-6 mb-6">
              <h2 className="text-lg font-semibold mb-4">Daily Cost (USD)</h2>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={metrics.by_day}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v.toFixed(3)}`} />
                  <Tooltip formatter={(v: number | undefined) => [v != null ? `$${v.toFixed(4)}` : "$0.0000", "Cost"]} />
                  <Bar dataKey="cost_usd" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Cost by model table */}
          {metrics.by_model.length > 0 && (
            <div className="bg-white rounded-lg border p-6">
              <h2 className="text-lg font-semibold mb-4">Cost by Model</h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="py-2 pr-4">Model</th>
                    <th className="py-2 pr-4">Cost</th>
                    <th className="py-2 pr-4">Prompt Tokens</th>
                    <th className="py-2 pr-4">Completion Tokens</th>
                    <th className="py-2">Calls</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.by_model.map((m) => (
                    <tr key={m.model} className="border-b">
                      <td className="py-2 pr-4 font-mono text-xs">{m.model}</td>
                      <td className="py-2 pr-4">${m.cost_usd.toFixed(4)}</td>
                      <td className="py-2 pr-4">{m.prompt_tokens.toLocaleString()}</td>
                      <td className="py-2 pr-4">{m.completion_tokens.toLocaleString()}</td>
                      <td className="py-2">{m.span_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {metrics.by_day.length === 0 && metrics.by_model.length === 0 && (
            <div className="border-2 border-dashed border-gray-200 rounded-lg p-12 text-center">
              <p className="text-gray-500">No cost data yet. Run agents with LLM calls to see analytics.</p>
            </div>
          )}
        </>
      )}
    </main>
  );
}
