# hamiGenZ — Product Requirements Document (PRD)

## Vision

hamiGenZ helps ordinary people in Nepal understand complex documents — passports,
government forms, notices, letters — by reading them, explaining them in simple
language, and showing the evidence behind every answer.

## Problem

Government documents in Nepal are hard to understand:
- Legal and technical language in Nepali and English
- Forms with fields people don't understand
- Deadlines and fees buried in dense text
- No easy way to ask "what does this mean?" or "how do I fill this?"

## Target Users

- Nepali citizens needing to fill government forms
- People who receive official notices they don't understand
- Anyone working with bilingual (Nepali/English) documents
- Users comfortable with English, Nepali script, or Romanized Nepali

## Core Capabilities

### Phase 1 (current MVP)

1. **Document upload** — PDF, PNG, JPG, TIFF
2. **Text extraction** — pdfplumber + PyMuPDF for PDFs, Tesseract OCR for images
3. **Question answering** — ask in English, Nepali, or Romanized Nepali
4. **Simple explanations** — three levels: original, simple, very simple
5. **Citations** — every answer shows page numbers and evidence excerpts
6. **Language detection** — auto-detect input language, respond in same language
7. **Form field explanation** — explain what each form field means
8. **Action extraction** — requirements, deadlines, fees, next steps, official links

### Phase 2 (upcoming)

1. Official Nepal knowledge base (passport, NID, traffic, govt services)
2. Trust signals: verified source badges, freshness warnings

## User Journey

1. User opens hamiGenZ
2. Uploads a document OR pastes text
3. Asks a question (or picks an example prompt)
4. Gets a simple explanation with citations
5. Can switch explanation level, language, or ask follow-ups
6. Can click citations to jump to evidence in the document
7. Can select text and ask "explain this"
8. Can see action items: what's needed, when, how much

## Non-Goals (for now)

- User accounts / authentication
- Multi-user document isolation
- Voice input / camera scanning
- PWA / mobile app
- Training custom models
- Web search / live internet lookup (except curated registry)

## Success Criteria

- A user can upload a Nepali government document and get a clear explanation
- Answers are grounded in the document, not hallucinated
- Evidence is shown with every claim
- Works in English, Nepali script, and Romanized Nepali
- Runs fully locally — no paid APIs, no cloud dependency
- Staging environment is publicly accessible for review

## Non-Functional Requirements

- **Local-first**: no external API calls, no cloud dependency
- **Free**: no paid services required to run
- **Fast enough**: page load < 3s, simple query < 15s on staging hardware
- **Safe**: uploaded documents stay private, no credential leakage
- **Honest**: says "I could not verify" rather than guessing
