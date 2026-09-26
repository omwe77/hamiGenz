---
type: DocumentType
title: Nepal Voter Identity Card (नेपाली मतदान परिचय पत्र / Voter ID)
description: "Nepal Voter ID card issued by the Election Commission of Nepal (नेपाल निर्वाचन आयोग). Used for voter identification and as a photo ID."
resource: https://election.gov.np
tags: [nepal, voter-id, election-commission, identity, official-id, voting, मतदान-परिचय-पत्र, नेपाली]
status: stable
generated: {by: "process/hamigenz-okf-curator/v0.1", at: "2026-09-25T00:00:00Z"}
sources:
  - {id: ecn, title: "Election Commission of Nepal", resource: "https://election.gov.np"}
owner: "Election Commission of Nepal / नेपाल निर्वाचन आयोग"
---

# Nepal Voter Identity Card

## What it is

The Nepal Voter Identity Card (मतदान परिचय पत्र) is issued by the Election Commission of Nepal (नेपाल निर्वाचन आयोग) to registered voters. It serves as proof of voter registration and as a photo ID document within Nepal.

## Document structure

The voter ID is typically a printed card/document with the following elements:

### Front side

- **नेपाल निर्वाचन आयोग** (Header) — "Election Commission of Nepal" at the top.
- **मतदान परिचय पत्र** — Title: "Voter Identity Card".
- **Photo** — Passport-sized photograph of the voter.
- **Name (नाम)** — Full name in Devanagari script.
- **Father's Name / Spouse's Name** (बाबुको नाम / सपत्नीको नाम) — Parent or spouse name.
- **Citizenship Number** (नागरिकता नम्बर) — Referenced citizenship number.
- **Voter ID Number** (मतदान ID नम्बर) — Unique voter registration number.
- **Polling Station / Constituency** (निर्वाचन क्षेत्र / मतदान केन्द्र) — Electoral constituency and polling station details.
- **District / Voter List location** — District, Village/Town, Ward details.
- **Date of issue / verification** — When the voter ID was issued or verified.
- **Issuing authority stamp/signature** — Election Commission seal.

### Back side (if applicable)

- Additional details, barcode, QR code.
- Security features.

## Voter ID number format

The voter ID number is typically an alphanumeric identifier, unique per voter registration. Format may vary by issuance year.

## OCR considerations

- Entirely in Devanagari script (some English numbers for dates and IDs).
- Photo + name are critical verification fields.
- May include constituency/polling station text in Nepali — good for location context but not identity-critical.
