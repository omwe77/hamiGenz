// app/workspace/[docId]/page.tsx
import { notFound } from "next/navigation";
import Link from "next/link";
import { getDocumentViewer } from "@/lib/hamigenz-api";
import DocViewerClient from "./DocViewerClient";

/**
 * Document home page (server-rendered).
 *
 * Each document has its own URL (/workspace/<docId>).
 * In demo mode, the sample document is pre-rendered at build time so recruiters
 * can directly open or refresh /workspace/demo-registration-form on Vercel.
 */
export async function generateStaticParams() {
  return [
    { docId: "demo-registration-form" },
  ];
}

async function getViewer(docId: string) {
  try {
    const res = await getDocumentViewer(docId);
    if (!res?.doc_id || !Array.isArray(res.pages)) notFound();
    return res;
  } catch {
    notFound();
  }
}

export default async function DocHomePage({
  params,
}: {
  params: Promise<{ docId: string }>;
}) {
  const { docId } = await params;
  const viewer = await getViewer(docId);

  return (
    <div>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-3)",
          padding: "var(--space-4) var(--space-6)",
          borderBottom: "1px solid var(--color-border)",
          background: "var(--color-surface)",
          marginBottom: "var(--space-5)",
        }}
      >
        <Link
          href="/workspace"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "var(--space-2)",
            color: "#c8520b",
            textDecoration: "none",
            fontWeight: "var(--font-semibold)",
          }}
        >
          <span aria-hidden="true">←</span> Workspace
        </Link>
        <span
          style={{
            flex: 1,
            textAlign: "right",
            fontSize: "var(--text-sm)",
            color: "var(--color-text-tertiary)",
          }}
        >
          {viewer.filename}
        </span>
      </header>
      <DocViewerClient
        docId={viewer.doc_id}
        pages={viewer.pages}
      />
    </div>
  );
}
