import assert from "node:assert/strict";
import {
  hasLiveBackend,
  isDemo,
  getDemoMode,
  setDemoModeState,
  listDocuments,
  getDocumentViewer,
  searchDocumentText,
  explainText,
  extractActions,
  detectFormFields,
  explainFormField,
  setFormFields,
  getFilledImage,
  submitFeedback,
  uploadDocument,
  deleteDocument,
  askGeneral,
} from "../src/lib/hamigenz-api.ts";

async function runDemoModeTests() {
  console.log("Starting Demo Mode automated verification suite...");

  // Intercept global fetch to guarantee NO network calls to localhost/127.0.0.1 happen in demo mode
  const originalFetch = globalThis.fetch;
  let fetchCallCount = 0;
  globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    fetchCallCount++;
    const url = String(input);
    if (url.includes("127.0.0.1") || url.includes("localhost") || url.includes("8000")) {
      throw new Error(`ACCIDENTAL LOCALHOST CALL DETECTED: ${url}`);
    }
    return originalFetch(input, init);
  };

  try {
    // 1. Verification of demo mode detection & state enforcement
    assert.strictEqual(typeof hasLiveBackend(), "boolean", "hasLiveBackend() should return a boolean");
    assert.strictEqual(isDemo(), true, "Default mode must be demo mode");
    assert.strictEqual(getDemoMode(), true, "getDemoMode() must match isDemo()");

    // 2. Switching to live mode without backend must be refused
    if (!hasLiveBackend()) {
      const switched = setDemoModeState(false);
      assert.strictEqual(switched, false, "setDemoModeState(false) must return false when no live backend is available");
      assert.strictEqual(isDemo(), true, "isDemo() must remain true after refused live toggle");
    }

    // 3. Document list
    const docs = await listDocuments();
    assert.ok(Array.isArray(docs), "listDocuments() must return an array");
    assert.ok(docs.length >= 1, "Must contain at least 1 sample document");
    const sampleDoc = docs.find((d) => d.doc_id === "demo-registration-form");
    assert.ok(sampleDoc, "Sample registration form must be present in documents list");
    assert.strictEqual(sampleDoc.filename, "registration_form_sample.pdf");
    console.log("✓ Document listing returns sample documents");

    // 4. Document viewer
    const viewer = await getDocumentViewer("demo-registration-form");
    assert.strictEqual(viewer.doc_id, "demo-registration-form");
    assert.ok(viewer.pages.length >= 1, "Must have at least 1 page");
    assert.ok(viewer.pages[0].text.includes("Registration form for the citizen"), "Must contain citizen registration text");
    assert.ok(viewer.pages[0].text.includes("Passport fees and required documents"), "Must contain passport notice text");
    assert.strictEqual(viewer.pages[0].has_image, true, "Must flag image availability");
    assert.strictEqual(viewer.pages[0].image_url, "/registration_form_sample.png", "Must point to sample PNG asset");
    console.log("✓ Document viewer returns verified sample content with page image");

    // 5. In-memory document search (no network calls)
    const searchPassport = await searchDocumentText("demo-registration-form", "passport");
    assert.ok(searchPassport.matches.length >= 1, "Should find occurrences of 'passport'");
    assert.strictEqual(searchPassport.matches[0].matched_term.toLowerCase(), "passport");
    assert.ok(searchPassport.matches[0].highlight_end > searchPassport.matches[0].highlight_start, "Valid highlight range");

    const searchRegistration = await searchDocumentText("demo-registration-form", "registration");
    assert.ok(searchRegistration.matches.length >= 1, "Should find occurrences of 'registration'");

    const searchEmpty = await searchDocumentText("demo-registration-form", "nonexistentquery123");
    assert.strictEqual(searchEmpty.matches.length, 0, "No matches for nonexistent query");
    console.log("✓ In-memory document text search finds matches with valid offsets");

    // 6. Explanations with verified citations and grounding
    const passportExplain = await explainText(
      "What documents are required for passport?",
      "simple",
      "english",
      "passport documents",
      "demo-registration-form"
    );
    assert.ok(passportExplain.explanation.answer.length > 20, "Must return comprehensive answer");
    assert.ok(passportExplain.citations.length >= 1, "Must contain citations");
    assert.ok(passportExplain.grounding?.confidence_score !== undefined, "Must include grounding report");
    assert.strictEqual(passportExplain.processing_time_ms, 0, "Processing time must be 0 in demo mode (no fake AI time)");
    assert.ok(passportExplain.explanation.grounding_note.includes("Demo sample"), "Must clearly label demo sample");

    const regExplain = await explainText(
      "How do I fill out a registration form?",
      "simple",
      "english",
      "registration form",
      "demo-registration-form"
    );
    assert.ok(regExplain.explanation.answer.includes("registration form"), "Must tailor answer to registration form");
    console.log("✓ Explanations return tailored answers with verified citations and clear demo notes");

    // 7. Action checklist extraction
    const actions = await extractActions("sample text", "demo-registration-form");
    assert.ok(actions.requirements.length >= 2, "Must contain requirements");
    assert.ok(actions.fees.length >= 1, "Must contain fees");
    assert.ok(actions.deadlines.length >= 1, "Must contain deadlines");
    assert.ok(actions.official_links.length >= 2, "Must include official government links");
    assert.strictEqual(actions.meta.status, "hints_only", "Must denote hints_only status");
    assert.ok(actions.meta.note?.includes("Demo sample"), "Meta note must state demo sample");
    console.log("✓ Action extraction provides comprehensive civic checklist and official links");

    // 8. Form understanding and field explanation
    const formDetect = await detectFormFields("sample form", "demo-registration-form");
    assert.strictEqual(formDetect.detection.is_form, true, "Must detect sample form");
    assert.ok(formDetect.fields.length >= 3, "Must detect form fields");

    const nameExp = await explainFormField("Full Name", { docId: "demo-registration-form" });
    assert.ok(nameExp.meaning.length > 10, "Must explain meaning");
    assert.ok(nameExp.belongs.length > 10, "Must guide what belongs");
    assert.ok(nameExp.do_not_enter.length > 10, "Must advise what not to enter");

    const fatherExp = await explainFormField("Father's Name", { docId: "demo-registration-form" });
    assert.ok(fatherExp.meaning.includes("father"), "Must tailor explanation to father field");
    console.log("✓ Form field detection and field-level assistance operate with honest guidance");

    // 9. Form saving and filling
    const saveRes = await setFormFields("demo-registration-form", [
      { id: "1", label: "Full Name", value: "Ram Bahadur" },
    ]);
    assert.strictEqual(saveRes.saved, true, "Form values saved locally in demo mode");

    const fillImageBlob = await getFilledImage("demo-registration-form", 1, [
      { id: "1", label: "Full Name", value: "Ram Bahadur" },
    ]);
    assert.ok(fillImageBlob instanceof Blob, "Returns blob for fill image");

    // 10. Feedback submission
    const feedback = await submitFeedback("What documents are required?", 1, "demo-registration-form");
    assert.strictEqual(feedback.status, "received");
    assert.ok(feedback.aggregate.total > 0, "Returns feedback aggregate");
    console.log("✓ Form values, image preview, and feedback endpoints function cleanly");

    // 11. Safe local upload and deletion
    const fakeFile = new File(["Sample document text"], "my_doc.txt", { type: "text/plain" });
    const uploadRes = await uploadDocument(fakeFile);
    assert.ok(uploadRes.doc_id.startsWith("demo-local-"), "Upload creates local demo doc ID");
    assert.ok(uploadRes.message.includes("Demo mode"), "Upload message clarifies local browser retention");

    await deleteDocument("demo-registration-form");
    console.log("✓ Local document upload and deletion operate without transmitting data");

    // 12. General Q&A
    const general = await askGeneral("What documents are required?");
    assert.strictEqual(general.provenance, "official_source");
    assert.ok(general.official_sources.length >= 1, "Includes curated official sources");
    console.log("✓ General asking endpoint provides source-grounded demo guidance");

    // Confirm that NO localhost fetches occurred
    assert.strictEqual(fetchCallCount, 0, `Expected 0 network fetches in demo mode, but recorded ${fetchCallCount}`);
    console.log("✓ Zero network fetches to localhost or 127.0.0.1 occurred during all operations!");

    console.log("\n=======================================================");
    console.log("ALL 12 DEMO MODE AUTOMATED CHECKS PASSED SUCCESSFULLY!");
    console.log("=======================================================\n");
  } finally {
    globalThis.fetch = originalFetch;
  }
}

runDemoModeTests().catch((err) => {
  console.error("DEMO MODE TEST FAILED:", err);
  process.exit(1);
});
