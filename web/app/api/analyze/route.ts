import { spawn } from "child_process";
import { readFileSync, unlinkSync, existsSync } from "fs";
import path from "path";

let running = false;

export async function POST(request: Request) {
  const origin = request.headers.get("origin") || "";
  if (origin) {
    try {
      const url = new URL(origin);
      if (url.hostname !== "localhost" && url.hostname !== "127.0.0.1") {
        return new Response("Forbidden", { status: 403 });
      }
    } catch {
      return new Response("Forbidden", { status: 403 });
    }
  }

  if (running) {
    return new Response("Analysis already in progress", { status: 429 });
  }
  running = true;

  const agentDir = path.resolve(process.cwd(), "..", "agent");
  const reportPath = path.join(agentDir, "report.html");
  const encoder = new TextEncoder();

  try {
    if (existsSync(reportPath)) unlinkSync(reportPath);
  } catch { /* ignore */ }

  let proc: ReturnType<typeof spawn> | null = null;
  let cancelled = false;

  const stream = new ReadableStream({
    start(controller) {
      function send(event: string, data: string) {
        if (cancelled) return;
        const encoded = data
          .split("\n")
          .map((line) => `data: ${line}`)
          .join("\n");
        controller.enqueue(
          encoder.encode(`event: ${event}\n${encoded}\n\n`)
        );
      }

      send("status", "Starting LinkedIn feed agent...");

      proc = spawn("python3", ["main.py"], {
        cwd: agentDir,
        env: { ...process.env },
      });

      proc.stdout!.on("data", (chunk: Buffer) => {
        const text = chunk.toString();
        for (const line of text.split("\n").filter(Boolean)) {
          if (line.startsWith("REPORT_FILE:")) {
            send("status", "Report generated. Loading...");
          } else {
            send("status", line);
          }
        }
      });

      proc.stderr!.on("data", (chunk: Buffer) => {
        const text = chunk.toString().trim();
        if (text) send("status", `[stderr] ${text}`);
      });

      proc.on("close", (code) => {
        running = false;
        if (cancelled) return;
        if (code === 0 && existsSync(reportPath)) {
          try {
            const html = readFileSync(reportPath, "utf-8");
            send("report", Buffer.from(html).toString("base64"));
          } catch {
            send("error", "Failed to read report file");
          }
        } else {
          send(
            "error",
            `Agent exited with code ${code}, no report generated`
          );
        }
        send("done", "complete");
        controller.close();
      });

      proc.on("error", (err) => {
        running = false;
        if (cancelled) return;
        send("error", err.message);
        controller.close();
      });
    },
    cancel() {
      cancelled = true;
      running = false;
      try { proc?.kill("SIGTERM"); } catch { /* already dead */ }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
