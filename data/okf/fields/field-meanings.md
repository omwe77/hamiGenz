---
type: FieldDefinition
title: Nepal Document Field Meanings — Reference
description: What common fields on Nepal official documents mean, what belongs there, and what to watch for.
tags: [fields, document-fields, meanings, nepali, identity-documents, reference, क्षेत्र, अर्थ, नेपाली, फेल्ड, पासपोर्ट]
status: stable
verified:
  - {by: "hamiGenZ OKF curator", at: "2025-09-24T00:00:00Z"}
owner: "hamiGenZ curated knowledge"
---

# Nepal Document Field Meanings — Reference

This concept explains what common fields on Nepal official documents (passports, citizenship certificates, NID cards, voter IDs) mean.

## Core identity fields

### नाम / Name (Given Names + Surname)

**What it is:** The full legal name of the document holder.

**What belongs here:**
- Full name as registered with the government — usually in Devanagari on Nepal documents.
- For passports: both Nepali and English versions may appear.
- Should match the citizenship certificate exactly for citizenship-based documents.

**Watch for:**
- Name changes (married women sometimes update surname) — old and new names may both appear.
- Typos in OCR — common Devanagari characters confused with each other.
- Hyphenated names, compound names — OCR may split or merge incorrectly.

### नागरिकता नम्बर / Citizenship Number

**What it is:** The unique citizenship identification number assigned to the person by the District Administration Office.

**What belongs here:**
- An alphanumeric identifier — format varies by issuance year and district.
- This is the primary key linking the person to the government's citizenship database.
- Present on citizenship certificates, NID cards, and often referenced on passports.

**Watch for:**
- Never confuse citizenship number with passport number — they are different identifiers.
- OCR may read digits as letters or vice versa in some fonts.

### पासपोर्ट नम्बर / Passport Number

**What it is:** The unique passport identifier assigned by the Passport Department.

**What belongs here:**
- Alphanumeric code — format like `A-XXXXXX` or `AB-XXXXXXX`.
- Present only on passports, not on citizenship certificates or NID cards.
- Changes when a new passport is issued (e.g., passport renewal).

**Watch for:**
- Passport number is different from citizenship number.
- MRZ (machine-readable zone) contains the passport number in encoded form — cross-check.

### जप्म मिति / Date of Birth

**What it is:** The person's date of birth.

**What belongs here:**
- Format: DD/MM/YYYY in Nepal (day-first).
- May appear in both Devanagari and English on passport data pages.
- Should be consistent across all identity documents for the same person.

**Watch for:**
- OCR may read `1` vs `7`, `0` vs `८` (Devanagari 8), `6` vs `९` (Devanagari 9) incorrectly.
- Day/month swap errors — always check DD/MM format, not MM/DD.

### लिंग / Gender

**What it is:** The gender of the document holder.

**What belongs here:**
- Male (पुलिंग / Male) or Female (स्त्रीलिंग / Female).
- On passports: sometimes abbreviated M/F.

**Watch for:**
- Rare OCR errors on gender — usually clear text, not ambiguous.

### ठेगाना / Address

**What it is:** The permanent or current address of the holder.

**What belongs here:**
- Full address: house number, ward/VDC, municipality, district, Nepal.
- Format varies — sometimes structured in fields, sometimes free-text.

**Watch for:**
- Addresses in rural areas may use VDC (Village Development Committee) terminology.
- Urban addresses may use ward and tole (street/neighborhood) names.

### पिताको नाम / Father's Name

**What it is:** The name of the document holder's father.

**What belongs here:**
- Father's full name as registered.
- Often required on citizenship certificates, passports, and many government forms.

**Watch for:**
- For women, sometimes husband's name (सपत्नीको नाम) appears instead or additionally.
- OCR errors on father's name are common because Devanagari names are long and contain rare characters.

### आमाको नाम / Mother's Name

**What it is:** The name of the document holder's mother.

**What belongs here:**
- Mother's full name as registered.
- Present on citizenship certificates and many forms.

**Watch for:**
- Same OCR challenges as father's name.

### जारी मिति / Issue Date

**What it is:** The date the document was issued.

**What belongs here:**
- DD/MM/YYYY format.
- Used to calculate expiry and verify document freshness.

**Watch for:**
- Issue date vs expiry date — don't confuse them.

### समाप्त मिति / Expiry Date

**What it is:** The date the document expires.

**What belongs here:**
- DD/MM/YYYY format.
- For passports: usually 5 or 10 years from issue date.
- For citizenship certificates: typically no expiry (citizenship is permanent).
- For NID cards: 5 or 10 years.

**Watch for:**
- Blank or missing expiry on documents that don't expire (citizenship).
- Expired documents are still valid for proving past identity but not for current transactions.

### हस्ताक्षर / Signature

**What it is:** The signature of the issuing authority (and sometimes the holder).

**What belongs here:**
- Issuing authority's signature + stamp/seal.
- Holder's signature on some documents (passports often have holder's signature).

**Watch for:**
- Stamp/seal authenticity is a key verification factor — blurred or missing stamps are suspicious.
- OCR may not capture signatures well — signatures are visual, not text.

## Document-specific fields

### Passport-specific

- **MRZ (Machine Readable Zone):** Bottom 2-3 lines of the data page — standardized encoded data. Parse separately, don't treat as body text.
- **Observation page:** May contain endorsements, restrictions, or notes.
- **Visa pages:** Blank pages for visa stamps — not part of the identity data.

### Citizenship certificate-specific

- **Certificate serial number:** District-specific format.
- **Blood group (रगत कunarो):** Sometimes on citizenship certificates.
- **Caste/Ethnicity (जाति/थर):** May appear on older certificates.

### NID card-specific

- **Card number:** Unique to the physical card, different from citizenship number.
- **Biometric chip:** Contactless smart card chip — not readable by OCR, but indicates document authenticity.

### Voter ID-specific

- **Constituency/Polling Station:** Electoral district information.
- **Voter list sequence number:** Position in the voter registry.
