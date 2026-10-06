---
type: DocumentType
title: Nepal Driving License (गाडी सबैभन्दा पत्र)
description: "Structure, fields, and regulations of the Nepal Driving License (गाडी सबैभन्दा पत्र) issued by the Traffic Police under the Ministry of Home Affairs."
resource: https://nepal.gov.np
tags: [nepal, traffic, driving-license, vehicle, official-id, license, दोस्रो परिचय, नामिन, निकाय]
status: stable
generated:
  by: "process/hamigenz-okf-curator/v0.1"
  at: "2026-09-25T00:00:00Z"
sources:
  - {id: traffic-police, title: "Traffic Police, Nepal", resource: "https://tp.gov.np"}
  - {id: moha, title: "Ministry of Home Affairs, Nepal", resource: "https://mhom.gov.np"}
owner: "Traffic Police, Ministry of Home Affairs"
---

# Nepal Driving License (गाडी सबैभन्दा पत्र)

## What it is

The Nepal **Driving License (गाडी सबैभन्दा पत्र / Licence)** is a government-issued document that permits a person to operate motor vehicles on public roads. It is issued by the **Traffic Police** under the **Ministry of Home Affairs**. The license also serves as a photo identity card within Nepal.

## License categories (vehicle classes)

The Nepal driving license covers multiple vehicle classes. The category shown on the license determines what the holder may legally drive:

- **B — Light motor vehicle** (गाडी — e.g. car, pick-up, jeep; motorcycles up to a stated engine capacity)
- **C — Medium/heavy vehicle** (bus, truck above a certain capacity)
- **D — Heavy/commercial vehicle** (large trucks, tankers, trailers)
- **E — Specialized/other vehicles** (tractors, road rollers, and other categories as classified)
- **Motorcycle-only license** (ठुलो साइकल / मोटरसायकल) — separate category for motorcycles

## Physical document structure

The driving license is a **PVC smart card** (similar to a bank card), typically with:

### Front side

- **नेपाल header** — National emblem/logo at top.
- **आगमन / लाइसेंस** — "Driving License" title.
- **Photo** — Passport-sized photograph of the holder.
- **Name (नाम)** — Full name in Devanagari.
- **Father's Name (बाबुको नाम)** — Father's full name.
- **Date of Birth (जन्म मिति)** — DD/MM/YYYY.
- **Gender (लिंग)** — Male / Female.
- **Address (ठेगाना)** — Permanent address.
- **Driving license number (नम्बर)** — Unique alphanumeric license number.
- **Card number (परिचय पत्र नम्बर)** — Unique card ID number (printed and encoded in chip).
- **Issue date / expiry date (जारी मिति / समाप्त मिति)** — Date of issue and expiry (usually 5 years from issue date).
- **Issuing authority (जारी गर्ने कार्यालय)** — Traffic Police, Ministry of Home Affairs.

### Back side

- **Barcode / QR code** — Machine-readable encoded data.
- **Driver license number / card number** — re-printed for machine scanning.
- **Blood group (रगत समूह)** — In some versions.
- **Vehicle categories licensed (योजना/वर्ग)** — The categories (B, C, D, E) the holder is licensed for.
- **Medical fitness certificate number** — If applicable.
- **Security features** — Hologram, UV features, microprinting.

## License number format

The driving license number is typically an **alphanumeric identifier**, unique per holder. Common patterns:

- A 7–9 character alphanumeric code, sometimes with a district prefix.
- The number may be printed on the front and encoded in the barcode/QR on the back.

## Vehicle categories explained

- **B (Light motor vehicle):** Cars, pick-up vans, jeeps, motorcycles up to the stated engine capacity. Most common category.
- **C (Medium/heavy vehicle):** Buses, cargo trucks below the heavy threshold.
- **D (Heavy/commercial vehicle):** Large trucks, tankers, vehicles with heavy payloads.
- **E (Specialized vehicles):** Tractors, road rollers, and other special-purpose vehicles.

## Medical fitness requirements

To obtain a driving license, the applicant must:

1. Pass a **vision test** (minimum vision standards).
2. Pass a **written / computerized test** on traffic rules and road signs (in Nepali and/or English).
3. Pass a **practical driving test** on public roads.
4. Provide a **medical fitness certificate** (where required) — must be fit to drive.

## Security features (for document verification)

- **Hologram** — Nepal emblem or traffic police logo visible when tilted.
- **UV features** — UV-reactive ink (e.g. "नेपाल", license number).
- **Microprinting** — Tiny text repeated in patterns.
- **Barcode/QR** — Machine-readable license and card numbers.
- **Signature of issuing authority** — Traffic Police officer's signature + seal.

## Important notes for OCR and document understanding

- The license is a **card**, not a booklet — scanning is straightforward.
- The name and date of birth are the most OCR-critical fields.
- Devanagari + English text appear side by side on the card.
- The **barcode/QR** contains structured data — parse separately from body text.
- See [Field meanings](fields/field-meanings.md) for what each field means.
- See [Driving license application](reference/driving-license-application.md) for how to apply.

## OCR considerations

- The card is **flat, laminated, and mostly paper/text + barcode**.
- Photo, name, and date of birth are the most important fields.
- The barcode/QR is machine-readable — do not feed it to the LLM as "document content."
- Devanagari and English may appear together on the same card.
