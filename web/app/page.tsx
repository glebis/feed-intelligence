"use client";

import { useState, useCallback, useRef, useEffect } from "react";

type Phase = "idle" | "running" | "done" | "error";

export default function Home() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [statusLines, setStatusLines] = useState<string[]>([]);
  const [reportHtml, setReportHtml] = useState<string>("");
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (phase !== "done" || !reportHtml || !iframeRef.current) return;
    const iframe = iframeRef.current;
    const handleMessage = (e: MessageEvent) => {
      if (
        e.source === iframe.contentWindow &&
        e.data?.type === "resize" &&
        typeof e.data.height === "number"
      ) {
        const h = Math.min(Math.max(e.data.height, 200), 50000);
        iframe.style.height = h + "px";
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [phase, reportHtml]);

  const runAnalysis = useCallback(async () => {
    setPhase("running");
    setStatusLines([]);
    setReportHtml("");

    try {
      const res = await fetch("/api/analyze", { method: "POST" });
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";

        for (const block of blocks) {
          const eventMatch = block.match(/^event: (\w+)/);
          if (!eventMatch) continue;

          const event = eventMatch[1];
          const dataLines = block
            .split("\n")
            .filter((l) => l.startsWith("data: "))
            .map((l) => l.slice(6));
          const data = dataLines.join("\n");

          if (event === "status") {
            setStatusLines((prev) => [...prev.slice(-20), data]);
          } else if (event === "report") {
            try {
              const bytes = Uint8Array.from(atob(data), (c) =>
                c.charCodeAt(0)
              );
              setReportHtml(new TextDecoder().decode(bytes));
            } catch {
              setReportHtml(data);
            }
            setPhase("done");
          } else if (event === "error") {
            setStatusLines((prev) => [...prev, `Error: ${data}`]);
            setPhase("error");
          }
        }
      }

      setPhase((prev) => (prev === "done" ? "done" : "error"));
    } catch (err) {
      setStatusLines((prev) => [...prev, `Error: ${err}`]);
      setPhase("error");
    }
  }, []);

  return (
    <div className="max-w-[900px] mx-auto px-8 py-12">
      {/* Header */}
      <div className="mb-12">
        <div className="mono text-[10px] tracking-[0.2em] uppercase text-[var(--text-muted)] mb-2">
          Feed Intelligence
        </div>
        <h1 className="text-2xl font-light text-white tracking-wide">
          LinkedIn Network Analysis
        </h1>
        <div className="mono text-[11px] text-[var(--text-muted)] mt-2 flex items-center gap-2">
          <span className="flex items-center gap-1.5">
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{
                background:
                  phase === "running"
                    ? "var(--accent)"
                    : phase === "done"
                      ? "#27ae60"
                      : "var(--text-muted)",
                animation:
                  phase === "running"
                    ? "pulse-dot 2s ease infinite"
                    : "none",
              }}
            />
            {phase === "idle" && "READY"}
            {phase === "running" && "ANALYZING"}
            {phase === "done" && "COMPLETE"}
            {phase === "error" && "ERROR"}
          </span>
        </div>
      </div>

      {/* Run Button */}
      {phase !== "done" && (
        <button
          onClick={runAnalysis}
          disabled={phase === "running"}
          className="mono flex items-center justify-center gap-2.5 mx-auto px-8 py-3.5 rounded-md text-[12px] tracking-[0.1em] uppercase text-white transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            background:
              phase === "running" ? "var(--text-muted)" : "var(--accent)",
          }}
        >
          <span className="w-2 h-2 rounded-full bg-white" />
          {phase === "running" ? "Analyzing..." : "Run Analysis"}
        </button>
      )}

      {/* Status Console */}
      {phase === "running" && statusLines.length > 0 && (
        <div className="mt-8 bg-[var(--surface)] rounded-md p-4 border border-[var(--border)]">
          <div className="mono text-[9px] tracking-[0.15em] uppercase text-[var(--text-muted)] mb-3">
            Status
          </div>
          <div className="mono text-[12px] text-[var(--text-dim)] space-y-1 max-h-48 overflow-y-auto">
            {statusLines.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
        </div>
      )}

      {/* Report in iframe */}
      {phase === "done" && reportHtml && (
        <>
          <div className="border-t border-[var(--border)] my-8" />
          <iframe
            ref={iframeRef}
            srcDoc={reportHtml}
            sandbox="allow-scripts allow-popups"
            className="w-full border-0 rounded-lg"
            style={{ minHeight: "600px" }}
            title="Feed Intelligence Report"
          />
        </>
      )}

      {/* Error State */}
      {phase === "error" && (
        <div className="mt-8 bg-[var(--surface)] border-l-2 border-[var(--accent)] rounded-r-md p-5">
          <div className="mono text-[9px] tracking-[0.15em] uppercase text-[var(--accent)] mb-2">
            Error
          </div>
          <p className="text-sm text-[var(--text-dim)]">
            Agent failed to produce a report. Check the status log above.
          </p>
          <button
            onClick={runAnalysis}
            className="mono mt-3 text-[11px] text-[var(--accent)] underline cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* Footer */}
      <div className="flex justify-between mt-12 pt-4 border-t border-[var(--border)] mono text-[10px] text-[#333]">
        <span>FEED INTELLIGENCE v0.1.0</span>
        <span>Powered by Claude Agent SDK</span>
      </div>
    </div>
  );
}
