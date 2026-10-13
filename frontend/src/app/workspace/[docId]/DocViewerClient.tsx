// app/workspace/[docId]/DocViewerClient.tsx
"use client";

import DocumentViewer from "@/components/workspace/DocumentViewer";
import type { ViewerPage, Citation, SearchMatch } from "@/lib/types";

/**
 * Thin client wrapper around DocumentViewer so the document home page can be
 * server-rendered while the viewer itself stays a client component.
 */
export default function DocViewerClient({
  docId,
  pages,
  onTextHighlight,
  citationsByPage,
  searchMatches,
  activeCitationPage,
  activeSearchMatchIdx,
  onActiveSearchMatchChange,
}: {
  docId: string;
  pages: ViewerPage[];
  onTextHighlight: (text: string) => void;
  citationsByPage: Map<number, Citation[]>;
  searchMatches: SearchMatch[];
  activeCitationPage: number | null;
  activeSearchMatchIdx: number | null;
  onActiveSearchMatchChange: (idx: number | null) => void;
}) {
  return (
    <DocumentViewer
      docId={docId}
      pages={pages}
      onTextHighlight={onTextHighlight}
      citationsByPage={citationsByPage}
      searchMatches={searchMatches}
      activeCitationPage={activeCitationPage}
      activeSearchMatchIdx={activeSearchMatchIdx}
      onActiveSearchMatchChange={onActiveSearchMatchChange}
    />
  );
}
