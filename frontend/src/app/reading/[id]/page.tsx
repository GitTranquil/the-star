"use client";

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import Header from "@/components/Header";
import { api } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface DrawnCard {
  card: { name: string };
  position_name: string;
  is_reversed: boolean;
}

export default function ReadingPage() {
  const { id } = useParams<{ id: string }>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [cards, setCards] = useState<DrawnCard[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load existing reading on mount
  useEffect(() => {
    const loadReading = async () => {
      try {
        const reading = await api.getReading(id) as Record<string, unknown>;
        const history = reading.conversation_history as Message[] | undefined;
        if (history) setMessages(history);
        const drawnCards = reading.cards_drawn as DrawnCard[] | undefined;
        if (drawnCards) setCards(drawnCards);
      } catch {
        // New reading — greeting will come from creation
      }
    };
    loadReading();
  }, [id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const response = (await api.sendMessage(id, userMessage)) as Record<string, unknown>;
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.message as string },
      ]);
      if (response.cards) {
        setCards(response.cards as DrawnCard[]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "I'm having trouble connecting. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Header />
      <main className="mx-auto flex max-w-3xl flex-col px-6 py-6" style={{ height: "calc(100vh - 65px)" }}>
        {/* Cards display */}
        {cards.length > 0 && (
          <div className="mb-4 flex justify-center gap-3">
            {cards.map((card, i) => (
              <div
                key={i}
                className={`rounded-lg border border-neutral-700 bg-neutral-900 p-3 text-center text-sm ${
                  card.is_reversed ? "rotate-180" : ""
                }`}
                style={{ minWidth: "100px" }}
              >
                <div className={`font-medium ${card.is_reversed ? "rotate-180" : ""}`}>
                  {card.card.name}
                </div>
                <div className={`text-xs text-neutral-400 mt-1 ${card.is_reversed ? "rotate-180" : ""}`}>
                  {card.position_name}
                  {card.is_reversed && " (R)"}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-4 pb-4">
          {messages.map((msg, i) => (
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
          {loading && (
            <div className="flex justify-start">
              <div className="rounded-xl bg-neutral-800 px-4 py-3 text-sm text-neutral-400">
                ...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={sendMessage} className="flex gap-2 pt-2 border-t border-neutral-800">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 rounded-lg border border-neutral-700 bg-neutral-900 px-4 py-3 text-sm focus:border-purple-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-lg bg-purple-600 px-5 py-3 text-sm font-medium hover:bg-purple-500 transition-colors disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </main>
    </>
  );
}
