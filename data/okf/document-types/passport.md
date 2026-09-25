---
type: DocumentType
title: Nepal Ordinary Passport
description: "Structure, fields, and pages of the Nepal ordinary passport (लामो राहदानी). 34-page and 66-page versions exist."
resource: https://nepalpassport.gov.np
tags: [nepal, identity, international-travel, official-id, passport, blue-passport, राहदानी, नेपाली, प्रवासी, डाटा पृष्ठ]
status: stable
generated: {by: "process/hamigenz-okf-curator/v0.1", at: "2026-09-25T00:00:00Z"}
verified:
  - {by: "process/hamigenz-okf-curator/v0.1", at: "2026-09-25T00:00:00Z"}
sources:
  - {id: passport-dept, title: "Nepal Department of Passports", resource: "https://nepalpassport.gov.np"}
owner: "Passport Department, Ministry of Foreign Affairs"
---

# Nepal Ordinary Passport

## What it is

The Nepal ordinary passport (नेपाली राहदानी) is issued by the Passport Department under the Ministry of Foreign Affairs. It is a blue-covered booklet used for international travel.

## Passport structure (page by page)

- A standard Nepal passport has **34 pages** (or 66 pages for frequent travelers). The pages are organized as follows:

### Page 1 — Data Page (प्रथम पृष्ठ / डाटा पृष्ठ)

This is the most important page. It contains the holder's personal information in both Nepali and English:

- **Passport No.** (पासपोर्ट नम्बर) — A unique alphanumeric identifier, usually starting with a letter followed by numbers (e.g., `A-123456` or `AB-1234567`). Located at the top.
- **Photo** — Passport-sized photograph of the holder, usually on the right side of the data page.
- **Surname / Last Name** (उपनाम / नाम) — In the Devanagari and English sections.
- **Given Names / First Name** (थर / नाम) — Full name in Devanagari and English.
- **Nationality** (राहदानी धारी / नागरिकता) — "Nepali" / "नेपाली"
- **Date of Birth** (जन्म मिति) — In DD/MM/YYYY format, in both scripts.
- **Place of Birth** (जन्म स्थान) — City/Town, District, Nepal.
- **Gender** (लिंग) — Male / Female / Other (नपुंसक / महिला / अन्य).
- **Issue Date** (जारी मिति) — When the passport was issued.
- **Expiry Date** (समाप्त मिति) — Usually 5 years or 10 years from issue date depending on passport type.
- **Date of Issue / Place of Issue** (जारी गर्ने ठेगाना) — The issuing authority office.
- **Authority** (अनुमति/अधिकारी) — Signature/stamp of issuing authority.
- **MRZ (Machine Readable Zone)** — The two or three lines of machine-readable text at the bottom of the data page, containing encoded passport data. Used for automated border control.

### Pages 2–3 — Observation / Endorsement Pages (अवलोकन पृष्ठ)

- Used for official endorsements, observations, or restrictions.
- May contain notes like "Observation: ..." or police verification notes.
- Often blank in normal passports.

### Pages 4–31 (or 4–63) — Visa Pages (भिसा पृष्ठहरू)

- Blank pages for visa stamps, entry/exit stamps, and border control annotations.
- Each page typically has:
  - "Nepal" watermark/logo
  - Space for visa stickers/stamps
  - Page number at the bottom

### Last Page — Personal Details / Security Page

- May contain additional holder information.
- Sometimes includes a second photo or emergency contact field.
- Security features: holograms, UV-reactive elements, microprinting, guilloche patterns.

## Security features (for document verification)

- **Hologram** — Usually on the data page, shows Nepal emblem or passport logo when tilted.
- **UV features** — UV-reactive ink visible under ultraviolet light.
- **Watermark** — "Nepal" or "राहदानी" visible when held to light.
- **Microprinting** — Tiny text repeated in patterns, visible under magnification.
- **Security thread** — Embedded thread, sometimes fluorescent.
- **Barcode / MRZ** — Machine-readable zone at the bottom of the data page.

## Document number format

Passport numbers in Nepal typically follow patterns like:

- `A-XXXXXX` (older format)
- `AB-XXXXXXX` (newer format)
- Alphanumeric, 6-8 characters

## Important notes for OCR and document understanding

- The data page contains the most critical fields — always extract from Page 1 first.
- Nepali and English text appear side by side on the data page.
- The MRZ at the bottom uses a standardized format (TD3 passport format) — 2 lines of 44 characters each.
- OCR should handle both Devanagari and Latin scripts on the same page.
- See [Field meanings](fields/field-meanings.md) for what each field on the data page means.
- See [How to apply](forms/fill-guidelines.md) for how to apply for a passport.
- The photo page should NOT be confused with visa pages — check the "नेपाल राहदानी" header.
