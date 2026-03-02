"use client";

import Link from "next/link";
import { RunSummary } from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    success: "bg-green-100 text-green-800",
    fail: "bg-red-100 text-red-800",
    running: "bg-yellow-100 text-yellow-800",
  };
  return (
    <span
      className={`px-2 py-1 rounded text-xs font-medium ${
        colors[status] || "bg-gray-100 text-gray-800"
      }`}
    >
      {status}
    </span>
  );
}

export function RunsTable({ runs }: { runs: RunSummary[] }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left text-gray-500">
          <th className="py-3 px-4">Name</th>
          <th className="py-3 px-4">Status</th>
          <th className="py-3 px-4">Duration</th>
          <th className="py-3 px-4">Tokens</th>
          <th className="py-3 px-4">Cost</th>
          <th className="py-3 px-4">Started</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <tr key={run.id} className="border-b hover:bg-gray-50">
            <td className="py-3 px-4">
              <Link
                href={`/runs/${run.id}`}
                className="text-blue-600 hover:underline font-medium"
              >
                {run.name || run.id}
              </Link>
            </td>
            <td className="py-3 px-4">
              <StatusBadge status={run.status} />
            </td>
            <td className="py-3 px-4">
              {run.duration_ms != null ? `${run.duration_ms}ms` : "—"}
            </td>
            <td className="py-3 px-4">
              {run.total_prompt_tokens + run.total_completion_tokens}
            </td>
            <td className="py-3 px-4">${run.total_cost_usd.toFixed(4)}</td>
            <td className="py-3 px-4">
              {run.started_at
                ? new Date(run.started_at).toLocaleString()
                : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
