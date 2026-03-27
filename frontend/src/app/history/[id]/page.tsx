"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Header from "@/components/Header";
import { api } from "@/lib/api";

interface ReadingDetail {
  id: string;
  mode: string;
  spread_type: string | null;
  summary: string | null;
  conversation_history: Array<{ role: string; content: string }>;
  cards_drawn: Array<{
    card: { name: string };
    position_name: string;
    is_reversed: boolean;
  }>;
  started_at: string;
  completed_at: string | null;
}

export default function ReadingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [reading, setReading] = useState<ReadingDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = (await api.getReading(id)) as ReadingDetail;
        setReading(data);
      } catch {
        // Not found
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  if (loading) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-3xl px-6 py-16">
          <p className="text-neutral-500">Loading...</p>
        </main>
      </>
    );
  }

  if (!reading) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-3xl px-6 py-16 text-center">
          <p className="text-neutral-400">Reading not found.</p>
          <Link href="/history" className="text-purple-400 mt-4 inline-block">
            Back to history
          </Link>
        </main>
      </>
    );
  }

  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-6 py-10">
        <Link href="/history" className="text-sm text-neutral-500 hover:text-neutral-300 mb-6 inline-block">
          &larr; Back to history
        </Link>

        <div className="flex items-center gap-3 mb-6">
          <h1 className="text-2xl font-bold capitalize">{reading.mode} Reading</h1>
          <span className="text-xs text-neutral-500">
            {new Date(reading.started_at).toLocaleDateString()}
          </span>
        </div>

        {reading.summary && (
          <p className="text-neutral-400 mb-6 text-sm border-l-2 border-purple-500 pl-4">
            {reading.summary}
          </p>
        )}

        {/* Cards */}
        {reading.cards_drawn?.length > 0 && (
          <div className="mb-8 flex justify-center gap-3">
            {reading.cards_drawn.map((card, i) => (
              <div
                key={i}
                className="rounded-lg border border-neutral-700 bg-neutral-900 p-3 text-center text-sm"
              >
                <div className="font-medium">{card.card.name}</div>
                <div className="text-xs text-neutral-400 mt-1">
                  {card.position_name}
                  {card.is_reversed && " (Reversed)"}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Conversation */}
        <div className="space-y-4">
          {reading.conversation_history?.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-purple-600/20 text-purple-100"
                    : "bg-neutral-800 text-neutral-200"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
        </div>
      </main>
    </>
  );
}
