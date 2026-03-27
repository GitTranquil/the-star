"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Header from "@/components/Header";
import { api } from "@/lib/api";

export default function NewReadingPage() {
  const [mode, setMode] = useState<"intuitive" | "traditional" | "custom">("intuitive");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const startReading = async () => {
    setLoading(true);
    try {
      const result = await api.createReading(mode);
      router.push(`/reading/${result.reading_id}`);
    } catch {
      setLoading(false);
    }
  };

  const modes = [
    {
      id: "intuitive" as const,
      name: "Intuitive",
      desc: "Warm, conversational, emotionally attuned",
    },
    {
      id: "traditional" as const,
      name: "Traditional",
      desc: "Classical Rider-Waite, formal, scholarly",
    },
    {
      id: "custom" as const,
      name: "Custom Deck",
      desc: "Your uploaded deck, visually interpreted",
      disabled: true,
    },
  ];

  return (
    <>
      <Header />
      <main className="mx-auto max-w-2xl px-6 py-16">
        <h1 className="text-3xl font-bold mb-2">New Reading</h1>
        <p className="text-neutral-400 mb-10">Choose your reading style.</p>

        <div className="space-y-3">
          {modes.map((m) => (
            <button
              key={m.id}
              onClick={() => !m.disabled && setMode(m.id)}
              disabled={m.disabled}
              className={`w-full rounded-lg border p-4 text-left transition-colors ${
                mode === m.id
                  ? "border-purple-500 bg-purple-500/10"
                  : "border-neutral-700 hover:border-neutral-600"
              } ${m.disabled ? "opacity-40 cursor-not-allowed" : ""}`}
            >
              <div className="font-medium">
                {m.name}
                {m.disabled && (
                  <span className="ml-2 text-xs text-neutral-500">Coming soon</span>
                )}
              </div>
              <div className="text-sm text-neutral-400 mt-1">{m.desc}</div>
            </button>
          ))}
        </div>

        <button
          onClick={startReading}
          disabled={loading}
          className="mt-8 w-full rounded-lg bg-purple-600 py-3 font-medium hover:bg-purple-500 transition-colors disabled:opacity-50"
        >
          {loading ? "Starting..." : "Begin Reading"}
        </button>
      </main>
    </>
  );
}
