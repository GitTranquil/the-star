"use client";

import { useState } from "react";
import Header from "@/components/Header";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";

export default function ProfilePage() {
  const { user } = useAuth();
  const [displayName, setDisplayName] = useState("");
  const [preferredMode, setPreferredMode] = useState("intuitive");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updateProfile({
        display_name: displayName || undefined,
        preferred_mode: preferredMode,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // Handle error
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Header />
      <main className="mx-auto max-w-lg px-6 py-16">
        <h1 className="text-3xl font-bold mb-8">Profile</h1>

        <div className="space-y-6">
          <div>
            <label className="block text-sm text-neutral-400 mb-1">Email</label>
            <p className="text-sm text-neutral-300">{user?.email}</p>
          </div>

          <div>
            <label htmlFor="name" className="block text-sm text-neutral-400 mb-1">
              Display Name
            </label>
            <input
              id="name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="How should the reader address you?"
              className="w-full rounded-md border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm text-neutral-400 mb-2">
              Preferred Reading Mode
            </label>
            <div className="space-y-2">
              {["intuitive", "traditional"].map((mode) => (
                <label key={mode} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="mode"
                    value={mode}
                    checked={preferredMode === mode}
                    onChange={() => setPreferredMode(mode)}
                    className="accent-purple-500"
                  />
                  <span className="text-sm capitalize">{mode}</span>
                </label>
              ))}
            </div>
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full rounded-md bg-purple-600 py-2 font-medium hover:bg-purple-500 transition-colors disabled:opacity-50"
          >
            {saving ? "Saving..." : saved ? "Saved!" : "Save Changes"}
          </button>
        </div>
      </main>
    </>
  );
}
