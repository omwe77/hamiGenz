# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary users are Nepali citizens, applicants, students, and migrant workers who must navigate complex government notices, official forms, citizenship documents, passports, and National IDs (NID).
- **Situation:** Users facing dense bureaucratic, legal, or technical phrasing in English, formal Nepali (Devanagari), or mixed scripts.
- **Job:** Understand what a document or form requires, verify fees and deadlines, clarify field meanings, and complete applications without fear of error or misinterpretation.

## Product Purpose

hamiGenZ is Nepal's AI document understanding platform — fully local, free, and offline-capable. It helps ordinary people understand complex documents by reading them, explaining them simply, and showing the direct evidence behind every answer. Success means a user can upload or reference any supported Nepali government document and obtain an accurate, transparent, and grounded explanation without hallucination.

## Positioning

"Don't understand it? Ask hamiGenZ."
Unlike general-purpose conversational LLMs or cloud document processors:
- **Local-first & Free:** Runs completely on-device or on local infrastructure with no paid cloud API dependency and zero document leaks.
- **Open Knowledge Format (OKF v0.2):** Powered by an authoritative, versioned Nepali government knowledge base paired with local vector search and OCR.
- **Strict Grounding Hierarchy:** Accuracy > Grounding > Usefulness > Simplicity > Visual polish. It explicitly answers "I could not verify this from an authoritative source" rather than hallucinating unsupported claims.

## Operating Context

- **Workflows:** Uploading PDFs or scans (citizenship, passport, NID, voter cards, public service notices), asking questions in Nepali script, Romanized Nepali, or English, toggling explanation levels (original, simple, very simple), and clicking citations to jump directly to document excerpts.
- **Environments:** Desktop and mobile web browsers across diverse network conditions in Nepal; usable even offline when running local backends.
- **Documents:** Nepal Ordinary Passport (34/66 pages), Nepal Citizenship Certificate, National ID (NID), Voter ID, and standard administrative forms.

## Capabilities and Constraints

- **Capabilities:**
  - Multi-source query routing (OKF curated knowledge, local FAISS vector search, official answer service, OCR post-processing).
  - Trilingual understanding: Devanagari script, Romanized Nepali, and English.
  - Granular evidence provenance: Page citations for uploaded documents, curated concept IDs and trust tiers for OKF references.
  - Multi-tier explanation simplification: original text, simple summary, and very simple breakdown.
- **Constraints:**
  - Local-first operation without mandatory external API keys or cloud dependencies.
  - No user accounts or authentication required for MVP.
  - Grounded answers only: answers must be supported by document excerpts or verified OKF entries.

## Brand Commitments

- **Name:** hamiGenZ
- **Tagline:** "Don't understand it? Ask hamiGenZ."
- **Voice:** Helpful, trustworthy, objective, and clear. Avoids robotic jargon or false confidence.

## Evidence on Hand

- Curated OKF knowledge bundle under `data/okf/` (passport, citizenship, national_id, voter_id, form fill guidelines, field meanings, OCR rules).
- Document parsing and OCR pipeline with 282 passing regression and conformance tests under `tests/`.
- Architectural specifications and PRD located in `docs/PRD.md`, `docs/ARCHITECTURE.md`, and `docs/SECURITY.md`.

## Product Principles

1. **Accuracy and Grounding Over Guesses:** Truthfulness and citations outrank fluent hallucinations. Always state unverified when evidence is absent.
2. **Accessible to Every Nepali:** First-class support for Devanagari script, Romanized Nepali, and English with plain-language simplification.
3. **Local, Private, and Sovereign:** User documents remain on local machines; no sensitive citizen records or credentials leave the user's boundary.
4. **Verifiable Provenance:** Every claim points directly to its source chunk or verified knowledge concept.
