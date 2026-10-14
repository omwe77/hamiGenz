/**
 * Reference-filled form preview panel.
 *
 * Lets the user request an example of how to complete an uploaded form:
 *  - detect form fields for the active document
 *  - type answers into each detected field
 *  - preview the original document page with example answers composited
 *    exactly onto their fields (original layout preserved)
 *  - download the composited PNG
 *
 * If field detection or alignment is unreliable, the panel shows a
 * field-by-field guide instead of a misleading image.
 *
 * Usage: <FillPanel docId={docId} />
 */
import { useEffect, useMemo, useState } from "react";
import { detectFormFields, setFormFields, getFilledImage } from "../../lib/hamigenz-api";
import type { FormDetectResponse, FormField, FormFieldValue } from "../../lib/types";

type Props = {
  docId: string | null;
};

function b64ToBlob(b64: string, mime = "image/png"): Blob {
  const bin = atob(b64.split(",")[1]);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Blob([bytes], { type: mime });
}

/** A field we can type an answer into. */
interface FieldEditor {
  id: string;
  label: string;
  page: number;
}

export default function FillPanel({ docId }: Props) {
  const [fields, setFields] = useState<FieldEditor[]>([]);
  const [values, setValues] = useState<FormFieldValue[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ png: string; width: number; height: number } | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showGuide, setShowGuide] = useState(false);

  // 1. Detect form fields on mount.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await detectFormFields(undefined, docId ?? undefined);
        if (cancelled) return;
        const fieldList: FieldEditor[] = (res.fields ?? []).map((f: FormField, i: number) => ({
          id: `${f.label}-${f.page}-${i}`,
          label: f.label,
          page: f.page ?? 1,
        }));
        setFields(fieldList);
        setValues(fieldList.map((f) => ({ label: f.label, value: "", page: f.page })));
        if (fieldList.length === 0) {
          setShowGuide(true);
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
  }, [docId]);

  // 2. Sync the values state if the field list changes.
  useEffect(() => {
    if (fields.length === 0) {
      setValues([]);
      return;
    }
    setValues(fields.map((f) => ({ label: f.label, value: "", page: f.page })));
  }, [fields]);

  const handleSave = async () => {
    if (values.some((v) => v.value.trim() === "")) {
      setError("Please fill in every field before saving.");
      return;
    }
    setSaving(true);
    try {
      await setFormFields(docId ?? "", values);
      setSaved(true);
      await new Promise((r) => setTimeout(r, 400));
      setSaved(false);
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
      const blob = await getFilledImage(docId ?? "", 1, values);
      const reader = new FileReader();
      reader.onload = () => {
        setPreview({ png: reader.result as string, width: 0, height: 0 });
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
    const blob = b64ToBlob(preview.png);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `form_filled_p${1}.png`;
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
          Overlay example answers onto the original document layout.
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
            I couldn't auto-detect the form fields on this page. Fill in the answers
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
              <button style={styles.secondaryBtn} onClick={handleDownload}>
                ↓ Download PNG
              </button>
            )}
          </div>

          {preview && (
            <div style={styles.previewBox}>
              <img
                src={`data:image/png;base64,${preview.png}`}
                alt="Filled form preview"
                style={styles.previewImg}
              />
              <p style={styles.previewCaption}>
                Page 1 — example answers composited onto the original layout.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Styles ─────────────────────────────────────────────────────
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
};
