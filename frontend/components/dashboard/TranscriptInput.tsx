"use client";

import { useState } from "react";
import { Send, Loader2 } from "lucide-react";

export function TranscriptInput() {
  const [transcript, setTranscript] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!transcript.trim()) return;

    setIsSubmitting(true);
    setStatus("idle");

    try {
      const res = await fetch(`${API_URL}/api/v1/incidents/process-call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript }),
      });

      if (res.ok) {
        setTranscript("");
        setStatus("success");
        setTimeout(() => setStatus("idle"), 2000);
      } else {
        setStatus("error");
      }
    } catch (err) {
      setStatus("error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex-1 p-3 flex flex-col gap-2 h-full">
      <div className="flex-1 relative">
        <textarea
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder="Enter emergency transcript (e.g. 'Fire in OP Jindal hostel, people trapped!')"
          className="w-full h-full resize-none bg-surface/50 border border-border rounded-md p-3 text-xs font-mono text-white placeholder:text-muted/50 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all"
          disabled={isSubmitting}
        />
      </div>
      <div className="flex items-center justify-between mt-1">
        <div className="text-[10px] font-mono text-muted flex items-center gap-2">
          {status === "success" && <span className="text-low">✓ INCIDENT INJECTED</span>}
          {status === "error" && <span className="text-critical">✗ INJECTION FAILED</span>}
        </div>
        <button
          type="submit"
          disabled={isSubmitting || !transcript.trim()}
          className="bg-primary/20 hover:bg-primary/30 border border-primary text-primary px-4 py-2 rounded-md font-mono text-xs flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          ANALYZE INCIDENT
        </button>
      </div>
    </form>
  );
}
