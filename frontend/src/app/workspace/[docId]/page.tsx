// app/workspace/[docId]/page.tsx
import { notFound } from "next/navigation";
import Link from "next/link";
import { getDocumentViewer } from "@/lib/hamigenz-api";
import DocViewerClient from "./DocViewerClient";
import type { ViewerPage, Citation, SearchMatch } from "@/lib/types";

/**
 * Document home page (server-rendered).
 *
 * Each uploaded document has its own URL (/workspace/<docId>). Selecting a
 * document navigates directly to its dedicated page instead of re-rendering
 * the shared workspace in place. The shared workspace (/workspace) stays the
 * browser for the document list.
 *
 * `generateStaticParams()` returns [] because document IDs are created at
 * runtime (uploaded documents) and are not known at build time. This route is
 * therefore client-navigable and fetches the viewer data on demand.
 */
export async function generateStaticParams() {
  return [];
}

async function getViewer(docId: string) {
  const res = await getDocumentViewer(docId);
  if (!res?.doc_id || !Array.isArray(res.pages)) notFound();
  return res;
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
        onTextHighlight={() => undefined}
        citationsByPage={new Map<number, Citation[]>()}
        searchMatches={[]}
        activeCitationPage={null}
        activeSearchMatchIdx={null}
        onActiveSearchMatchChange={() => undefined}
      />
    </div>
  );
}
