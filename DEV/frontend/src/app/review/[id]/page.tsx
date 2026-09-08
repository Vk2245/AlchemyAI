"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Save, AlertTriangle, CheckCircle, ShieldCheck } from "lucide-react";


export default function ReviewPage() {
  const { id } = useParams();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entities, setEntities] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchRecord = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          router.push("/login");
          return;
        }

        const res = await fetch(`http://127.0.0.1:6104/api/records/${id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!res.ok) throw new Error("Failed to load record");

        const json = await res.json();
        setData(json);

        // Extract entities for editing
        if (json.document_record?.record_data?.entities) {
          setEntities(json.document_record.record_data.entities);
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchRecord();
  }, [id, router]);

  const handleEntityChange = (index: number, newValue: string) => {
    const newEntities = [...entities];
    newEntities[index].value = newValue;
    // When a human edits, we consider it verified
    newEntities[index].human_verified = true;
    newEntities[index].confidence = 1.0;
    setEntities(newEntities);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem("token");

      const payload = {
        record_data: {
          ...data.document_record.record_data,
          entities: entities,
        }
      };

      const res = await fetch(`http://127.0.0.1:6104/api/review/${id}/verify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Failed to save verification");

      // Navigate back to record view
      router.push(`/record/${id}`);
    } catch (err: any) {
      alert("Error saving: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  if (error || !data) {
    return <div className="min-h-screen flex items-center justify-center text-red-500">{error}</div>;
  }

  const docRecord = data.document_record;

  return (
    <div className="min-h-screen flex flex-col items-center pt-24 pb-12 px-6">
      <div className="w-full max-w-5xl space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between glass-panel p-6 rounded-2xl border border-[var(--border)]">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-[var(--border)] rounded-full transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-2xl font-bold">Human-in-the-Loop Review</h1>
              <p className="text-[var(--secondary)] text-sm">
                Verify and edit extracted data before final tamper-proof sealing.
              </p>
            </div>
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 bg-[var(--accent-primary)] hover:opacity-90 text-white px-6 py-2.5 rounded-full transition-all font-medium disabled:opacity-50"
          >
            {saving ? "Saving..." : "Verify & Save"}
            <ShieldCheck className="w-4 h-4" />
          </button>
        </div>

        {/* Info Banner */}
        <div className="glass-panel p-6 rounded-2xl border border-[var(--border)] flex flex-col gap-2">
          <h2 className="text-lg font-semibold text-[var(--accent-primary)]">{docRecord?.document_title}</h2>
          <div className="text-sm text-[var(--secondary)] flex gap-4">
            <span>Type: {docRecord?.document_type}</span>
            <span>Party: {docRecord?.primary_party}</span>
          </div>
        </div>

        {/* Table */}
        <div className="glass-panel rounded-2xl border border-[var(--border)] overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[var(--border)] text-sm text-[var(--secondary)]">
                <th className="p-4 font-medium w-1/4">Entity Type</th>
                <th className="p-4 font-medium w-2/4">Extracted Value</th>
                <th className="p-4 font-medium w-1/4">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {entities.map((ent, idx) => {
                const isLowConfidence = ent.confidence < 0.85 && !ent.human_verified;

                return (
                  <tr key={idx} className="border-b border-[var(--border)] last:border-0 hover:bg-white/5 transition-colors">
                    <td className="p-4">
                      <span className="text-sm font-medium bg-white/10 px-2 py-1 rounded-md">
                        {ent.entity_type}
                      </span>
                    </td>
                    <td className="p-4">
                      <input
                        type="text"
                        value={ent.value}
                        onChange={(e) => handleEntityChange(idx, e.target.value)}
                        className={`w-full bg-transparent border-b outline-none px-2 py-1 transition-colors ${isLowConfidence
                            ? "border-amber-500/50 text-amber-100"
                            : "border-transparent focus:border-[var(--accent-primary)]"
                          }`}
                      />
                    </td>
                    <td className="p-4 flex items-center gap-2">
                      {ent.human_verified ? (
                        <span className="flex items-center gap-1 text-emerald-400 text-sm">
                          <CheckCircle className="w-4 h-4" /> Verified
                        </span>
                      ) : isLowConfidence ? (
                        <span className="flex items-center gap-1 text-amber-500 text-sm">
                          <AlertTriangle className="w-4 h-4" /> {(ent.confidence * 100).toFixed(0)}%
                        </span>
                      ) : (
                        <span className="text-emerald-400 text-sm">
                          {(ent.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {entities.length === 0 && (
                <tr>
                  <td colSpan={3} className="p-8 text-center text-[var(--secondary)]">
                    No entities extracted.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

      </div>
    </div>
  );
}
