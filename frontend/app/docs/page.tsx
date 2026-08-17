"use client";

import { useEffect, useState, type DragEvent, type FormEvent } from "react";
import DocumentCard from "@/components/DocumentCard";
import { useApp } from "@/lib/AppContext";
import { DOCUMENT_TYPES, fetchDocuments, uploadDocument, type DocumentMeta } from "@/lib/api";

export default function DocsPage() {
  const { activePersona, personasError } = useApp();
  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [docsError, setDocsError] = useState<string | null>(null);
  const [loadingDocs, setLoadingDocs] = useState(false);

  const [docType, setDocType] = useState<string>("i20");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  // Pure reset when the active account changes — safe during render (not an
  // effect-only-to-setState pattern), matching lib/AppContext.tsx's approach.
  const [resetFor, setResetFor] = useState<string | null>(null);
  const activeAccountId = activePersona?.id ?? null;
  if (activeAccountId !== resetFor) {
    setResetFor(activeAccountId);
    setDocs([]);
    setDocsError(null);
    setLoadingDocs(activeAccountId !== null);
  }

  function reload(personaId: string) {
    setLoadingDocs(true);
    fetchDocuments(personaId)
      .then(setDocs)
      .catch((e) => setDocsError(e instanceof Error ? e.message : "Failed to load documents"))
      .finally(() => setLoadingDocs(false));
  }

  useEffect(() => {
    if (!activePersona) return;
    let cancelled = false;
    fetchDocuments(activePersona.id)
      .then((d) => {
        if (!cancelled) setDocs(d);
      })
      .catch((e) => {
        if (!cancelled) setDocsError(e instanceof Error ? e.message : "Failed to load documents");
      })
      .finally(() => {
        if (!cancelled) setLoadingDocs(false);
      });
    return () => {
      cancelled = true;
    };
    // Switching accounts must show the new account's documents, not a stale list.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activePersona?.id]);

  async function doUpload(chosenFile: File) {
    if (!activePersona) return;
    setUploading(true);
    setUploadError(null);
    try {
      await uploadDocument(activePersona.id, docType, chosenFile);
      setFile(null);
      reload(activePersona.id);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  function handleUpload(e: FormEvent) {
    e.preventDefault();
    if (file) doUpload(file);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragActive(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) doUpload(dropped);
  }

  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-900">Docs</h1>
      <p className="mt-1 mb-6 text-sm text-slate-500">
        Your admission letter, job offer letter, ISSS eligibility letter, and other paperwork in one place.
      </p>

      {(personasError || docsError) && (
        <p className="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {personasError ?? docsError}
        </p>
      )}

      {activePersona && (
        <>
          <section
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            className={`rounded-2xl border-2 border-dashed p-6 text-center shadow-sm transition-colors ${
              dragActive ? "border-blue-400 bg-blue-50" : "border-blue-200 bg-white"
            }`}
          >
            <p className="text-sm font-medium text-slate-700">Drag a file here, or choose one below</p>
            <form onSubmit={handleUpload} className="mt-3 flex flex-wrap items-center justify-center gap-2">
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="rounded-full border border-slate-300 px-3 py-1.5 text-sm"
              >
                {Object.entries(DOCUMENT_TYPES).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <input
                type="file"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="text-sm text-slate-600 file:mr-2 file:rounded-full file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-blue-800"
              />
              <button
                type="submit"
                disabled={!file || uploading}
                className="rounded-full bg-blue-700 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-blue-800 disabled:opacity-50"
              >
                {uploading ? "Uploading…" : "Upload"}
              </button>
            </form>
            {uploadError && <p className="mt-2 text-sm text-red-600">{uploadError}</p>}
            <p className="mt-2 text-xs text-slate-400">
              Stored for your reference only — nothing here changes your plan or is sent to anyone automatically.
            </p>
          </section>

          <section className="mt-4">
            <h2 className="mb-2 font-medium text-slate-900">Your documents</h2>
            {loadingDocs && <p className="text-sm text-slate-400">Loading…</p>}
            {!loadingDocs && docs.length === 0 && (
              <p className="text-sm text-slate-400">Nothing uploaded yet.</p>
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              {docs.map((doc) => (
                <DocumentCard key={doc.id} personaId={activePersona.id} doc={doc} />
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
