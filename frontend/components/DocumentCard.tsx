import { DOCUMENT_TYPES, documentFileUrl, type DocumentMeta } from "@/lib/api";

// Seeded (system-provided, not user-uploaded) document types get a visible
// sample banner — these reuse Texas A&M's real name for credibility, so they
// must never be mistakable for genuine institutional correspondence. See
// backend/app/data/seed_documents/ and DECISIONS.md.
const SEEDED_TYPES = new Set(["admit_letter", "job_offer"]);

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentCard({ personaId, doc }: { personaId: string; doc: DocumentMeta }) {
  const isSeeded = SEEDED_TYPES.has(doc.doc_type);

  return (
    <div className="relative overflow-hidden rounded-2xl border border-blue-100 bg-white shadow-sm">
      {isSeeded && (
        <div className="bg-red-50/95 px-3 py-1 text-center text-[11px] font-medium text-red-700">
          SAMPLE DOCUMENT — not official
        </div>
      )}
      <div className="p-4">
        <p className="text-xs font-semibold tracking-wide text-blue-700 uppercase">
          {DOCUMENT_TYPES[doc.doc_type] ?? doc.doc_type}
        </p>
        <p className="mt-1 truncate text-sm font-medium text-slate-900">{doc.filename}</p>
        <p className="mt-1 text-xs text-slate-500">
          {formatSize(doc.size_bytes)} · {new Date(doc.uploaded_at).toLocaleDateString()}
        </p>
        <a
          href={documentFileUrl(personaId, doc.id)}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-block rounded-full border border-blue-200 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-blue-50"
        >
          View
        </a>
        {isSeeded && (
          <p className="mt-2 text-[11px] text-slate-400">
            Generated for this demo — not a real document from Texas A&amp;M University.
          </p>
        )}
      </div>
    </div>
  );
}
