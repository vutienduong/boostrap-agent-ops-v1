"use client";

import { useEffect, useState } from "react";
import { fetchRuns, RunSummary } from "@/lib/api";
import { RunsTable } from "@/components/runs-table";

const PROJECT_ID = "01JDEFAULTPROJECT000000";

export default function HomePage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRuns(PROJECT_ID)
      .then((data) => setRuns(data.runs))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="max-w-6xl mx-auto p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Agent Runs</h1>
        <p className="text-sm text-gray-500 mt-1">
          Track and debug your AI agent executions
        </p>
      </div>

      {loading && <p className="text-gray-500">Loading runs...</p>}
      {error && (
        <p className="text-red-500">
          Failed to load runs. Is the API server running?
        </p>
      )}
      {!loading && !error && runs.length === 0 && (
        <div className="border-2 border-dashed border-gray-200 rounded-lg p-12 text-center">
          <p className="text-gray-500 font-medium">No runs yet</p>
          <p className="text-gray-400 text-sm mt-1">
            Install the SDK and add{" "}
            <code className="bg-gray-100 px-1 rounded">@agentops.track()</code>{" "}
            to your agent to get started.
          </p>
        </div>
      )}
      {!loading && !error && runs.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border">
          <RunsTable runs={runs} />
        </div>
      )}
    </main>
  );
}
