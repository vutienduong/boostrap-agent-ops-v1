"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchRun, RunDetail } from "@/lib/api";
import { SpanTimeline } from "@/components/span-timeline";

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.runId as string;
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRun(runId)
      .then(setRun)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) return <p className="p-8 text-gray-500">Loading...</p>;
  if (!run) return <p className="p-8 text-red-500">Run not found</p>;

  return (
    <main className="max-w-6xl mx-auto p-8">
      <Link href="/" className="text-blue-600 hover:underline text-sm">
        ← Back to runs
      </Link>

      <div className="mt-4 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {run.name || run.id}
        </h1>
        <div className="flex gap-6 mt-2 text-sm text-gray-500">
          <span>
            Status:{" "}
            <strong
              className={
                run.status === "success" ? "text-green-600" : "text-red-600"
              }
            >
              {run.status}
            </strong>
          </span>
          <span>
            Duration:{" "}
            {run.duration_ms != null ? `${run.duration_ms}ms` : "—"}
          </span>
          <span>
            Tokens:{" "}
            {run.total_prompt_tokens + run.total_completion_tokens}
          </span>
          <span>Cost: ${run.total_cost_usd.toFixed(4)}</span>
        </div>
      </div>

      <h2 className="text-lg font-semibold mb-3 text-gray-800">
        Spans Timeline
      </h2>
      {run.spans.length === 0 ? (
        <p className="text-gray-500">No spans recorded.</p>
      ) : (
        <SpanTimeline spans={run.spans} />
      )}
    </main>
  );
}
