"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchRun, RunDetail, createReplay, getReplay, ReplayResponse } from "@/lib/api";
import { SpanTimeline } from "@/components/span-timeline";

function ReplayPanel({ runId }: { runId: string }) {
  const [model, setModel] = useState("gpt-4o-mini");
  const [temperature, setTemperature] = useState(0.7);
  const [replay, setReplay] = useState<ReplayResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleReplay = async () => {
    setLoading(true);
    try {
      const r = await createReplay(runId, { model, temperature });
      setReplay(r);
      // Poll for completion
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        const updated = await getReplay(r.id);
        setReplay(updated);
        if (updated.status === "done" || updated.status === "failed" || attempts > 20) {
          clearInterval(poll);
          setLoading(false);
        }
      }, 1500);
    } catch {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg border mt-6 p-6">
      <h2 className="text-lg font-semibold mb-4">Replay Run</h2>
      <div className="flex gap-4 items-end mb-4">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Model override</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          >
            <option value="gpt-4o-mini">gpt-4o-mini</option>
            <option value="gpt-4o">gpt-4o</option>
            <option value="claude-3-5-sonnet-20241022">claude-3-5-sonnet</option>
            <option value="claude-3-haiku-20240307">claude-3-haiku</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Temperature</label>
          <input
            type="number"
            min={0}
            max={2}
            step={0.1}
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
            className="border rounded px-2 py-1 text-sm w-20"
          />
        </div>
        <button
          onClick={handleReplay}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Running..." : "Replay"}
        </button>
      </div>

      {replay && (
        <div className="mt-3 text-sm">
          <p className="text-gray-500">
            Replay status:{" "}
            <strong
              className={
                replay.status === "done"
                  ? "text-green-600"
                  : replay.status === "failed"
                  ? "text-red-600"
                  : "text-yellow-600"
              }
            >
              {replay.status}
            </strong>
          </p>
          {replay.new_run_id && (
            <a
              href={`/runs/${replay.new_run_id}`}
              className="text-blue-600 hover:underline mt-1 block"
            >
              View replayed run →
            </a>
          )}
        </div>
      )}
    </div>
  );
}

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

      <ReplayPanel runId={runId} />
    </main>
  );
}
