import Link from "next/link";
import Header from "@/components/Header";

export default function Home() {
  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-6 py-24 text-center">
        <h1 className="text-5xl font-bold tracking-tight">
          Tarot Agent
        </h1>
        <p className="mt-4 text-lg text-neutral-400">
          AI-powered tarot readings that remember you.
        </p>
        <p className="mt-2 text-neutral-500">
          Every reading builds on the last. Your reader remembers your story.
        </p>
        <div className="mt-10 flex justify-center gap-4">
          <Link
            href="/reading"
            className="rounded-lg bg-purple-600 px-6 py-3 font-medium hover:bg-purple-500 transition-colors"
          >
            Start a Reading
          </Link>
          <Link
            href="/login"
            className="rounded-lg border border-neutral-700 px-6 py-3 font-medium hover:bg-neutral-800 transition-colors"
          >
            Sign In
          </Link>
        </div>
      </main>
    </>
  );
}
