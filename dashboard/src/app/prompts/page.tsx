"use client";

import { useEffect, useState } from "react";
import { fetchPromptVersions, PromptVersion } from "@/lib/api";

const PROJECT_ID = "01JDEFAULTPROJECT000000";

function groupByKey(versions: PromptVersion[]): Record<string, PromptVersion[]> {
  return versions.reduce((acc, pv) => {
    if (!acc[pv.key]) acc[pv.key] = [];
    acc[pv.key].push(pv);
    return acc;
  }, {} as Record<string, PromptVersion[]>);
}

export default function PromptsPage() {
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [selected, setSelected] = useState<[PromptVersion | null, PromptVersion | null]>([null, null]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPromptVersions(PROJECT_ID)
      .then((d) => setVersions(d.versions))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const grouped = groupByKey(versions);

  return (
    <main className="max-w-6xl mx-auto p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Prompt Versions</h1>
        <p className="text-sm text-gray-500 mt-1">Track and compare prompt changes over time</p>
      </div>

      {loading && <p className="text-gray-500">Loading...</p>}

      {!loading && versions.length === 0 && (
        <div className="border-2 border-dashed border-gray-200 rounded-lg p-12 text-center">
          <p className="text-gray-500">No prompt versions yet.</p>
          <p className="text-gray-400 text-sm mt-1">
            Use <code className="bg-gray-100 px-1 rounded">agentops.prompt_version(key, version, content)</code> in your agent.
          </p>
        </div>
      )}

      {Object.entries(grouped).map(([key, pvs]) => (
        <div key={key} className="bg-white rounded-lg border mb-4">
          <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
            <span className="font-mono font-medium text-sm">{key}</span>
            <span className="text-xs text-gray-500">{pvs.length} version{pvs.length !== 1 ? "s" : ""}</span>
          </div>
          <div className="divide-y">
            {pvs.map((pv) => (
              <div key={pv.id} className="px-4 py-3 flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                      v{pv.version}
                    </span>
                    <span className="text-xs text-gray-400">
                      {new Date(pv.created_at).toLocaleString()}
                    </span>
                  </div>
                  <pre className="text-xs text-gray-700 bg-gray-50 p-2 rounded overflow-auto max-h-32 whitespace-pre-wrap">
                    {pv.content}
                  </pre>
                </div>
                <div className="flex flex-col gap-1 shrink-0">
                  <button
                    onClick={() => setSelected([pv, selected[1]])}
                    className={`text-xs px-2 py-1 rounded border ${
                      selected[0]?.id === pv.id
                        ? "bg-blue-600 text-white border-blue-600"
                        : "text-gray-600 border-gray-300 hover:bg-gray-50"
                    }`}
                  >
                    A
                  </button>
                  <button
                    onClick={() => setSelected([selected[0], pv])}
                    className={`text-xs px-2 py-1 rounded border ${
                      selected[1]?.id === pv.id
                        ? "bg-purple-600 text-white border-purple-600"
                        : "text-gray-600 border-gray-300 hover:bg-gray-50"
                    }`}
                  >
                    B
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Diff panel */}
      {selected[0] && selected[1] && (
        <div className="bg-white rounded-lg border mt-6">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h2 className="font-semibold text-sm">
              Comparing v{selected[0].version} &rarr; v{selected[1].version}
            </h2>
          </div>
          <div className="grid grid-cols-2 divide-x">
            <div className="p-4">
              <p className="text-xs font-semibold text-blue-600 mb-2">A &mdash; v{selected[0].version}</p>
              <pre className="text-xs bg-blue-50 p-2 rounded overflow-auto whitespace-pre-wrap">
                {selected[0].content}
              </pre>
            </div>
            <div className="p-4">
              <p className="text-xs font-semibold text-purple-600 mb-2">B &mdash; v{selected[1].version}</p>
              <pre className="text-xs bg-purple-50 p-2 rounded overflow-auto whitespace-pre-wrap">
                {selected[1].content}
              </pre>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
