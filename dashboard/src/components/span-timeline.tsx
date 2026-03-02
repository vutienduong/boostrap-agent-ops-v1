"use client";

import { useState } from "react";
import { Span } from "@/lib/api";

function SpanRow({ span }: { span: Span }) {
  const [expanded, setExpanded] = useState(false);
  const typeColors: Record<string, string> = {
    llm: "border-l-blue-500",
    tool: "border-l-orange-500",
    retrieval: "border-l-purple-500",
    custom: "border-l-gray-400",
  };

  return (
    <div
      className={`border-l-4 ${
        typeColors[span.type] || "border-l-gray-300"
      } bg-white rounded shadow-sm mb-2`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-gray-50"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono bg-gray-100 px-2 py-0.5 rounded">
            {span.type}
          </span>
          <span className="font-medium text-sm">{span.name}</span>
          {span.model && (
            <span className="text-xs text-gray-500">{span.model}</span>
          )}
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>{span.tokens_prompt + span.tokens_completion} tokens</span>
          <span>
            {span.duration_ms != null ? `${span.duration_ms}ms` : "—"}
          </span>
          <span
            className={
              span.status === "success" ? "text-green-600" : "text-red-600"
            }
          >
            {span.status}
          </span>
        </div>
      </button>
      {expanded && (
        <div className="px-4 pb-4 border-t">
          {span.input_json && (
            <div className="mt-2">
              <p className="text-xs font-semibold text-gray-500 mb-1">Input</p>
              <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-48">
                {JSON.stringify(span.input_json, null, 2)}
              </pre>
            </div>
          )}
          {span.output_json && (
            <div className="mt-2">
              <p className="text-xs font-semibold text-gray-500 mb-1">
                Output
              </p>
              <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-48">
                {JSON.stringify(span.output_json, null, 2)}
              </pre>
            </div>
          )}
          {span.error_json && (
            <div className="mt-2">
              <p className="text-xs font-semibold text-red-500 mb-1">Error</p>
              <pre className="text-xs bg-red-50 p-2 rounded overflow-auto max-h-48">
                {JSON.stringify(span.error_json, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function SpanTimeline({ spans }: { spans: Span[] }) {
  return (
    <div className="space-y-1">
      {spans.map((span) => (
        <SpanRow key={span.id} span={span} />
      ))}
    </div>
  );
}
