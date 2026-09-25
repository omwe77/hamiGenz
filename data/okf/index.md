---
type: Index
title: hamiGenZ Knowledge Bundle
description: "Curated knowledge about Nepal official documents, identity cards, and form-filling processes."
tags: [hamigenz, knowledge-bundle, nepal, official-documents]
status: stable
okf_version: "0.2"
generated: {by: "process/hamigenz-okf-curator/v0.1", at: "2026-09-25T00:00:00Z"}
verified:
  - {by: "process/hamigenz-okf-curator/v0.1", at: "2026-09-25T00:00:00Z"}
---

# hamiGenZ Knowledge Bundle

This bundle contains curated knowledge about Nepal official documents,
identity cards, and form-filling processes.

## How to use this bundle

- Each concept is a single markdown file with YAML frontmatter.
- Concepts are organized by directory: `document-types/`, `forms/`, `ocr/`, `fields/`.
- Cross-reference concepts using standard Markdown links: `[text](path/to/concept.md)`.
- The bundle is version-controlled in git — changes are diffable and reviewable.

## Concept types used in this bundle

- **DocumentType** — describes a specific Nepal official document (passport, citizenship, etc.)
- **FormGuide** — guidelines for filling out a specific form or form type
- **OCRRule** — post-processing rules for OCR output from Nepali documents
- **FieldDefinition** — what a specific field on a document means

## Questions this bundle answers

- "What is a Nepal passport and what are its pages?"
- "What does the citizenship certificate look like?"
- "What field is on page 3 of the voter ID?"
- "How do I fill out this form?"
- "What OCR corrections should I apply to Nepali text?"

## Directory structure

* [Document Types](document-types/) — Passport, Citizenship, NID, Voter ID
* [Field Definitions](fields/) — What each field on Nepal documents means
* [Form Filling Guidelines](forms/) — How to fill Nepal government forms
* [OCR Post-Processing Rules](ocr/) — Rules for cleaning OCR output
