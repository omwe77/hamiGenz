---
type: DocumentType
title: Nepal Citizenship Certificate (नागरिकता प्रमाणपत्र)
description: "Structure and fields of the Nepal Citizenship Certificate — the primary proof of Nepali citizenship."
resource: https://nepal.gov.np
tags: [nepal, citizenship, identity, official-id, citizenship-certificate, नागरिकता, नेपाली, प्रमाणपत्र, नागरिक]
status: stable
generated: {by: "process/hamigenz-okf-curator/v0.1", at: "2026-09-25T00:00:00Z"}
verified:
  - {by: "process/hamigenz-okf-curator/v0.1", at: "2026-09-25T00:00:00Z"}
sources:
  - {id: moha, title: "Ministry of Home Affairs, Nepal", resource: "https://mhom.gov.np"}
owner: "District Administration Office, Ministry of Home Affairs"
---

# Nepal Citizenship Certificate

## What it is

The Nepal Citizenship Certificate (नागरिकता प्रमाणपत्र) is the official document proving Nepali citizenship. It is issued by the District Administration Office (जिल्ला प्रशासन कार्यालय) under the Ministry of Home Affairs.

## Physical document structure

### Front side (पुस्ता १)

- **नेपाल गणराज्य** (Header) — "नेपाल" with national emblem/seal at top.
- **नागरिकता प्रमाणपत्र** — Title: "Citizenship Certificate" in Nepali.
- **Serial number / प्रमाणपत्र नम्बर** — A unique certificate number, usually in format `XXXX/XXX` or similar.
- **Photo** — Passport-sized photograph of the holder.
- **Name (थर/नाम)** — Full name in Devanagari script.
- **Father's Name (बाबुको नाम)** — Father's full name.
- **Mother's Name (आमाको नाम)** — Mother's full name.
- **Date of Birth** (जन्म मिति) — DD/MM/YYYY format.
- **Place of Birth** (जन्म स्थान) — Village/Town, District, Nepal.
- **Gender** (लिंग) — Male / Female.
- **Address** (ठेगाना) — Permanent address (स्थायी ठेगाना).
- **Issue Date** (जारी मिति) — Date the certificate was issued.
- **Issuing Authority** (जारी गर्ने अधिकारी) — District Administration Office name, with signature/stamp/seal.

### Back side (पुस्ता २ — if applicable)

- Additional details like blood group, caste/ethnicity (जाति/थर), permanent address verification.
- Security stamp/seal.
- May have renewal/endorsement information.

## Citizenship categories

The Citizenship Certificate is issued under the Citizenship Act. Categories include citizenship by birth, naturalized citizenship, and citizenship for persons of Nepali origin. The specific category is indicated on the certificate.

## Verification notes

- The certificate has a district administration office stamp and typically a background watermark.
- Tampering indicators: mismatched fonts, blurry stamp, photo replacement signs.
- Verification checksums are NOT typically present — visual inspection + issuing authority database check is the norm.

## OCR considerations

- Entirely in Devanagari script (mostly) — ensure the Nepali traineddata model is used.
- Some English numbers may appear (dates, certificate numbers).
- The name section is the most OCR-critical field.
