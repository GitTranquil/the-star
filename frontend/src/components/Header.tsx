"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

export default function Header() {
  const { user, loading, signOut } = useAuth();

  return (
    <header className="border-b border-neutral-800 px-6 py-4">
      <nav className="mx-auto flex max-w-4xl items-center justify-between">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Tarot Agent
        </Link>

        {!loading && (
          <div className="flex items-center gap-6 text-sm">
            {user ? (
              <>
                <Link
                  href="/reading"
                  className="text-neutral-400 hover:text-neutral-100 transition-colors"
                >
                  New Reading
                </Link>
                <Link
                  href="/history"
                  className="text-neutral-400 hover:text-neutral-100 transition-colors"
                >
                  History
                </Link>
                <Link
                  href="/profile"
                  className="text-neutral-400 hover:text-neutral-100 transition-colors"
                >
                  Profile
                </Link>
                <button
                  onClick={signOut}
                  className="text-neutral-500 hover:text-neutral-300 transition-colors"
                >
                  Sign out
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="rounded-md bg-neutral-800 px-4 py-2 text-sm hover:bg-neutral-700 transition-colors"
              >
                Sign in
              </Link>
            )}
          </div>
        )}
      </nav>
    </header>
  );
}
