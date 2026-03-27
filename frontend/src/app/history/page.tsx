"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import { api } from "@/lib/api";

interface Reading {
  id: string;
  mode: string;
  spread_type: string | null;
  dominant_theme: string | null;
  status: string;
  started_at: string;
}

export default function HistoryPage() {
  const [readings, setReadings] = useState<Reading[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = (await api.listReadings()) as unknown as Reading[];
        setReadings(data);
      } catch {
        // No readings yet
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <>
      <Header />
      <main className="mx-auto max-w-2xl px-6 py-16">
        <h1 className="text-3xl font-bold mb-8">Reading History</h1>

        {loading ? (
          <p className="text-neutral-500">Loading...</p>
        ) : readings.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-neutral-400 mb-4">No readings yet.</p>
            <Link
              href="/reading"
              className="text-purple-400 hover:text-purple-300"
            >
              Start your first reading
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {readings.map((r) => (
              <Link
                key={r.id}
                href={`/history/${r.id}`}
                className="block rounded-lg border border-neutral-700 p-4 hover:border-neutral-600 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium capitalize">
                    {r.mode} reading
                  </span>
                  <span className="text-xs text-neutral-500">
                    {new Date(r.started_at).toLocaleDateString()}
                  </span>
                </div>
                {r.dominant_theme && (
                  <p className="text-sm text-neutral-400 mt-1">
                    {r.dominant_theme}
                  </p>
                )}
                <div className="flex gap-2 mt-2">
                  {r.spread_type && (
                    <span className="text-xs text-neutral-500 bg-neutral-800 rounded px-2 py-0.5">
                      {r.spread_type}
                    </span>
                  )}
                  <span
                    className={`text-xs rounded px-2 py-0.5 ${
                      r.status === "completed"
                        ? "text-green-400 bg-green-400/10"
                        : "text-yellow-400 bg-yellow-400/10"
                    }`}
                  >
                    {r.status}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
