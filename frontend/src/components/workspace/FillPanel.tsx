import { useEffect, useRef, useState } from "react";
import { detectFormFields, setFormFields, getFilledImage } from "../../lib/hamigenz-api";
import type { FormField, FormFieldValue, FormPreviewState } from "../../lib/types";

// The blank registration form is a public asset served at the site root (/blank_form.png).
const BLANK_FORM_URL = "/blank_form.png";

type Props = {
  docId: string | null;
  demoMode: boolean;
};

function dataUrlToBlob(dataUrl: string): Blob {
  const parts = dataUrl.split(",");
  const base64 = parts.length > 1 ? parts[1] : parts[0];
  const bin = atob(base64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Blob([bytes], { type: "image/png" });
}

interface FieldEditor {
  id: string;
  label: string;
  page: number;
}

/** Demo field values for reference-filled form preview. */
const DEMO_FIELDS: FieldEditor[] = [
  { id: "full-name", label: "Full name", page: 1 },
  { id: "fathers-name", label: "Father's name", page: 1 },
  { id: "dob", label: "Date of birth", page: 1 },
  { id: "district", label: "District", page: 1 },
  { id: "nationality", label: "Nationality", page: 1 },
  { id: "present-address", label: "Present address", page: 1 },
  { id: "permanent-address", label: "Permanent address", page: 1 },
  { id: "phone", label: "Phone number", page: 1 },
];

/** Demo synthetic values for demo fields. */
const DEMO_VALUES: FormFieldValue[] = [
  { label: "Full name", value: "SARABJEET RAI", page: 1, id: "full-name" },
  { label: "Father's name", value: "SOURAV RAIMAL RAI", page: 1, id: "fathers-name" },
  { label: "Date of birth", value: "15 March 1998", page: 1, id: "dob" },
  { label: "District", value: "Kathmandu", page: 1, id: "district" },
  { label: "Nationality", value: "Nepali", page: 1, id: "nationality" },
  { label: "Present address", value: "Kathmandu 44600, Nepal", page: 1, id: "present-address" },
  { label: "Permanent address", value: "Kathmandu 44600, Nepal", page: 1, id: "permanent-address" },
  { label: "Phone number", value: "9841012345", page: 1, id: "phone" },
];

/** Asynchronously render edited values onto a canvas with a blank form background, returning a full PNG data URL. */
function renderPreviewCanvas(
  imageSrc: string,
  values: FormFieldValue[],
  width = 800,
  height = 600
): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("Unable to create canvas 2D context"));
          return;
        }

        // Draw blank form template background
        ctx.drawImage(img, 0, 0, width, height);

        // Field positions matching blank_form.png layout
        const fieldPositions: Record<string, { x: number; y: number; w: number; h: number }> = {
          "full-name": { x: 300, y: 80, w: 240, h: 34 },
          "fathers-name": { x: 300, y: 130, w: 240, h: 34 },
          "dob": { x: 300, y: 180, w: 240, h: 34 },
          "district": { x: 300, y: 230, w: 240, h: 34 },
          "nationality": { x: 300, y: 280, w: 240, h: 34 },
          "present-address": { x: 300, y: 330, w: 240, h: 34 },
          "permanent-address": { x: 300, y: 380, w: 240, h: 34 },
          "phone": { x: 300, y: 430, w: 240, h: 34 },
        };

        const font = "14px Arial, sans-serif";
        for (const v of values) {
          const pos = fieldPositions[v.id];
          if (!pos) continue;
          ctx.fillStyle = "#1a1a2e";
          ctx.font = font;
          ctx.textAlign = "left";
          ctx.fillText(v.value, pos.x + 8, pos.y + 22);
        }

        resolve(canvas.toDataURL("image/png"));
      } catch (err) {
        reject(err);
      }
    };
    img.onerror = () => {
      reject(new Error(`Failed to load background template image from ${imageSrc}`));
    };
    img.src = imageSrc;
  });
}

export default function FillPanel({ docId, demoMode }: Props) {
  const [fields, setFields] = useState<FieldEditor[]>([]);
  const [values, setValues] = useState<FormFieldValue[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<FormPreviewState | null>(null);
  const [saving, setSaving] = useState(false);
  const isDemoMode = Boolean(demoMode && docId === "demo-registration-form");
  const [showGuide, setShowGuide] = useState(false);

  // Sequence ref to ensure stale async renders never overwrite newer edits
  const renderSeqRef = useRef(0);

  const updateDemoPreview = async (currentValues: FormFieldValue[]) => {
    const seq = ++renderSeqRef.current;
    try {
      const dataUrl = await renderPreviewCanvas(BLANK_FORM_URL, currentValues);
      if (seq === renderSeqRef.current) {
        setPreview({ dataUrl, width: 800, height: 600 });
        setError(null);
      }
    } catch (e) {
      if (seq === renderSeqRef.current) {
        const msg = e instanceof Error ? e.message : String(e);
        console.error("Failed to render demo preview:", msg);
        setError(`Preview error: ${msg}`);
      }
    }
  };

  // 1. Detect form fields on mount / docId change.
  useEffect(() => {
    let cancelled = false;
    if (!docId) {
      return;
    }
    (async () => {
      try {
        setLoading(true);
        setError(null);
        if (isDemoMode) {
          // Demo mode: return static sample form fields and trigger initial canvas render
          const demoFields = DEMO_FIELDS.map((f) => ({
            ...f,
            demoValue: DEMO_VALUES.find((v) => v.id === f.id)?.value ?? "",
          }));
          setFields(demoFields);
          const initialValues = demoFields.map((f) => ({ label: f.label, value: f.demoValue, page: f.page, id: f.id }));
          setValues(initialValues);
          updateDemoPreview(initialValues);
        } else {
          const res = await detectFormFields(undefined, docId ?? undefined);
          if (cancelled) return;
          const fieldList: FieldEditor[] = (res.fields ?? []).map((f: FormField, i: number) => ({
            id: `${f.label}-${f.page}-${i}`,
            label: f.label,
            page: f.page ?? 1,
          })) as FieldEditor[];
          setFields(fieldList);
          setValues(fieldList.map((f) => ({ label: f.label, value: "", page: f.page, id: f.id })));
          if (fieldList.length === 0) {
            setShowGuide(true);
          }
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [docId, isDemoMode]);

  const handleSave = async () => {
    if (values.some((v) => v.value.trim() === "")) {
      setError("Please fill in every field before saving.");
      return;
    }
    setSaving(true);
    try {
      await setFormFields(docId ?? "", values);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handlePreview = async () => {
    setLoading(true);
    setError(null);
    try {
      if (isDemoMode) {
        await updateDemoPreview(values);
        return;
      }
      const blob = await getFilledImage(docId ?? "", 1, values);
      const reader = new FileReader();
      reader.onload = () => {
        setPreview({ dataUrl: reader.result as string, width: 800, height: 600 });
      };
      reader.readAsDataURL(blob);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPreview(null);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!preview) return;
    const blob = dataUrlToBlob(preview.dataUrl);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = isDemoMode
      ? "registration_form_sample_filled.png"
      : "form_filled_p1.png";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!docId) {
    return (
      <div style={styles.empty}>
        <p>Select a document to enable reference-filled previews.</p>
      </div>
    );
  }

  return (
    <div style={styles.root}>
      <div style={styles.header}>
        <h3>Reference-filled form preview</h3>
        <span style={styles.subtitle}>
          {demoMode ? "Illustrative example — not official information." : "Overlay example answers onto the original document layout."}
        </span>
      </div>

      {error && <div style={styles.errorBox}>{error}</div>}

      {loading && <div style={styles.placeholder}>Detecting form fields…</div>}

      {!loading && fields.length === 0 && !showGuide && !error && (
        <div style={styles.empty}>
          <p>No form fields detected. Upload a form and try again.</p>
        </div>
      )}

      {!loading && showGuide && fields.length === 0 && (
        <div style={{ ...styles.empty, ...styles.guideBox }}>
          <p>
            I couldn&apos;t auto-detect the form fields on this page. Fill in the answers
            in the guide below — they will be overlaid onto the original layout.
          </p>
          <p style={styles.subnote}>
            Sample values are clearly marked as placeholders (they are not real data).
          </p>
        </div>
      )}

      {!loading && fields.length > 0 && (
        <div style={styles.body}>
          <div style={styles.fieldList}>
            <div style={styles.fieldListHeader}>
              <span>Field</span>
              <span>Answer</span>
            </div>
            {fields.map((f) => (
              <div key={f.id} style={styles.fieldRow}>
                <div style={styles.fieldLabel}>{f.label}</div>
                <input
                  style={styles.textInput}
                  value={values.find((v) => v.label === f.label)?.value ?? ""}
                  onChange={(e) => {
                    const next = values.map((v) =>
                      v.label === f.label ? { ...v, value: e.target.value } : v
                    );
                    setValues(next);
                    if (isDemoMode) {
                      updateDemoPreview(next);
                    }
                  }}
                  placeholder="Type answer here…"
                  aria-label={`Answer for ${f.label}`}
                />
              </div>
            ))}
          </div>

          <div style={styles.actions}>
            <button
              style={styles.primaryBtn}
              onClick={handleSave}
              disabled={saving || values.some((v) => v.value.trim() === "")}
            >
              {saving ? "Saving…" : "Save answers"}
            </button>
            <button
              style={styles.secondaryBtn}
              onClick={handlePreview}
              disabled={loading}
            >
              {loading ? "Rendering preview…" : "Preview filled page"}
            </button>
            {preview && (
              <button style={styles.secondaryBtn} onClick={handleDownload} aria-label="Download filled form image" title="Download filled form as PNG">
                ↓ Download PNG
              </button>
            )}
          </div>

          {preview && (
            <div style={styles.previewBox}>
              <img
                src={preview.dataUrl}
                alt="Filled form preview"
                style={styles.previewImg}
              />
              <p style={styles.previewCaption}>
                Example answers composited onto the original document layout.
                {demoMode && <span style={styles.demoNote}> Illustrative example — not official information.</span>}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Styles ──────────────────────────────────────────────────────
const styles: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-3)",
    padding: "var(--space-4)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-xl)",
  },
  header: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-1)",
  },
  subtitle: {
    fontSize: "var(--text-sm)",
    color: "var(--color-text-tertiary)",
  },
  errorBox: {
    padding: "var(--space-3)",
    background: "var(--color-error-bg)",
    border: "1px solid var(--color-error-border)",
    borderRadius: "var(--radius-md)",
    color: "var(--color-error-text)",
    fontSize: "var(--text-sm)",
  },
  placeholder: {
    padding: "var(--space-4)",
    color: "var(--color-text-tertiary)",
    fontSize: "var(--text-sm)",
  },
  empty: {
    padding: "var(--space-4)",
    color: "var(--color-text-tertiary)",
    fontSize: "var(--text-sm)",
  },
  guideBox: {
    border: "1px dashed var(--color-citation-border)",
    background: "rgba(245, 158, 11, 0.04)",
  },
  subnote: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
    marginTop: 0,
  },
  body: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-3)",
  },
  fieldList: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  },
  fieldListHeader: {
    display: "grid",
    gridTemplateColumns: "1fr 2fr",
    gap: "var(--space-2)",
    fontSize: "var(--text-xs)",
    fontWeight: "var(--font-medium)",
    color: "var(--color-text-tertiary)",
    padding: "var(--space-2) 0",
    borderBottom: "1px solid var(--color-border)",
  },
  fieldRow: {
    display: "grid",
    gridTemplateColumns: "1fr 2fr",
    gap: "var(--space-2)",
    alignItems: "center",
  },
  fieldLabel: {
    fontSize: "var(--text-xs)",
    color: "var(--color-text-secondary)",
    fontWeight: "var(--font-medium)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  textInput: {
    padding: "var(--space-2) var(--space-3)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    backgroundColor: "var(--color-bg-alt)",
    fontSize: "var(--text-sm)",
    outline: "none",
  },
  actions: {
    display: "flex",
    gap: "var(--space-2)",
    flexWrap: "wrap",
  },
  primaryBtn: {
    padding: "var(--space-2) var(--space-4)",
    background: "var(--color-primary)",
    color: "var(--color-primary-text)",
    border: "none",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-medium)",
    cursor: "pointer",
  },
  secondaryBtn: {
    padding: "var(--space-2) var(--space-4)",
    background: "var(--color-bg-alt)",
    color: "var(--color-text-primary)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    fontSize: "var(--text-sm)",
    fontWeight: "var(--font-medium)",
    cursor: "pointer",
  },
  previewBox: {
    marginTop: "var(--space-3)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    overflow: "hidden",
    background: "var(--color-bg-alt)",
  },
  previewImg: {
    width: "100%",
    height: "auto",
    maxHeight: "400px",
    objectFit: "contain",
  },
  previewCaption: {
    padding: "var(--space-2)",
    fontSize: "var(--text-xs)",
    color: "var(--color-text-tertiary)",
  },
  demoNote: {
    marginLeft: "var(--space-2)",
    fontSize: "var(--text-xs)",
    color: "#e65100",
    fontWeight: "var(--font-medium)",
  },
};
