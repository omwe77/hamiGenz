// app/workspace/[docId]/DocViewerClient.tsx
"use client";

import { useMemo } from "react";
import DocumentViewer from "@/components/workspace/DocumentViewer";
import type { ViewerPage, Citation } from "@/lib/types";

/**
 * Client wrapper around DocumentViewer providing default client callbacks.
 * Server component DocHomePage passes serializable data (docId, pages).
 */
export default function DocViewerClient({
  docId,
  pages,
}: {
  docId: string;
  pages: ViewerPage[];
}) {
  const citationsByPage = useMemo(() => new Map<number, Citation[]>(), []);

  return (
    <DocumentViewer
      docId={docId}
      pages={pages}
      onTextHighlight={() => undefined}
      citationsByPage={citationsByPage}
      searchMatches={[]}
      activeCitationPage={null}
      activeSearchMatchIdx={null}
      onActiveSearchMatchChange={() => undefined}
    />
  );
}
