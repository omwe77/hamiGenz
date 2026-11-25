#!/usr/bin/env bash
# test_docker_persistence.sh
# Docker named-volume persistence test for hamiGenZ (M3 validation).
#
# Verifies:
#   1. UID/GID 10001 (non-root) can write to the named volume.
#   2. An uploaded document survives a container stop + recreate using the same volume.
#   3. A deleted document and its vector artifacts are removed from the volume.
#
# Usage (CI): run after `docker build -t hamigenz-backend:ci .`
# and after the host HF cache is provisioned at $MODEL_CACHE_DIR.
# Requires: bash, curl, jq, docker.
set -euo pipefail

IMAGE="${1:-hamigenz-backend:ci}"
VOLUME="hamigenz-data-persist-test"
CONTAINER="hamigenz-persist-test"
PORT=18001
BASE_URL="http://localhost:${PORT}"
# Stable >=32-char secret across container stop/recreate so signed session tokens remain valid.
SESSION_SECRET="$(od -An -tx1 -N32 /dev/urandom | tr -d ' \n')"
HDR_FILE="$(mktemp /tmp/persist_hdr_XXXXXX.txt)"
SESSION_TOKEN=""

cleanup() {
  echo "--- Cleaning up ---"
  rm -f "${HDR_FILE}"
  docker rm -f "${CONTAINER}" 2>/dev/null || true
  docker volume rm -f "${VOLUME}" 2>/dev/null || true
}
trap cleanup EXIT

echo "=== Step 1: Create named volume and start container ==="
docker volume create "${VOLUME}"
docker run -d \
  --name "${CONTAINER}" \
  -p "${PORT}:8000" \
  -e PORT=8000 \
  -e HF_HUB_OFFLINE=1 \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HAMIGENZ_SESSION_SECRET="${SESSION_SECRET}" \
  -v "${VOLUME}:/app/backend/data" \
  ${MODEL_CACHE_DIR:+-v "${MODEL_CACHE_DIR}:/app/backend/data/huggingface:ro"} \
  "${IMAGE}"

echo "--- Waiting for /health ---"
for i in $(seq 1 30); do
  if curl -sf "${BASE_URL}/health" > /dev/null; then
    echo "PASS: /health returned 200 (attempt $i)"
    break
  fi
  [ "$i" -eq 30 ] && { echo "ERROR: container did not become healthy"; docker logs "${CONTAINER}"; exit 1; }
  sleep 2
done

echo ""
echo "=== Step 2: Verify UID/GID 10001 write access to volume ==="
docker exec "${CONTAINER}" sh -c '
  id
  test "$(id -u)" = "10001" && echo "PASS: UID is 10001 (non-root)"
  test "$(id -g)" = "10001" && echo "PASS: GID is 10001 (non-root)"
  touch /app/backend/data/uploads/.write_test && rm /app/backend/data/uploads/.write_test && echo "PASS: uploads writable by UID 10001"
  touch /app/backend/data/vectors/.write_test && rm /app/backend/data/vectors/.write_test && echo "PASS: vectors writable by UID 10001"
'

echo ""
echo "=== Step 3: Upload a synthetic test document ==="
# Create a minimal valid PDF with extractable text using PyMuPDF inside the image
# (a blank 1x1 image yields zero chunks and is rejected by /upload).
TMPFILE="$(mktemp /tmp/persist_test_XXXXXX.pdf)"
docker run --rm "${IMAGE}" python -c \
  "import fitz, sys; doc=fitz.open(); p=doc.new_page(); p.insert_text((72,72),'hamiGenZ Docker persistence test document.'); sys.stdout.buffer.write(doc.tobytes())" \
  > "${TMPFILE}"

UPLOAD_RESP=$(curl -sf -D "${HDR_FILE}" -X POST "${BASE_URL}/upload" \
  -F "file=@${TMPFILE};filename=persist_test.pdf;type=application/pdf")
rm -f "${TMPFILE}"

SESSION_TOKEN=$(grep -i '^x-session-token:' "${HDR_FILE}" | awk '{print $2}' | tr -d '\r\n')
[ -z "${SESSION_TOKEN}" ] && { echo "ERROR: upload response did not issue X-Session-Token"; exit 1; }

echo "Upload response: ${UPLOAD_RESP}"
DOC_ID=$(echo "${UPLOAD_RESP}" | jq -r '.doc_id')
[ -z "${DOC_ID}" ] || [ "${DOC_ID}" = "null" ] && { echo "ERROR: upload did not return doc_id"; exit 1; }
echo "PASS: Document uploaded — doc_id=${DOC_ID}"

echo ""
echo "=== Step 4: Verify artifacts exist on the named volume ==="
docker exec "${CONTAINER}" sh -c "
  found=\$(find /app/backend/data/uploads -name '*${DOC_ID}*' | wc -l)
  [ \"\$found\" -ge 1 ] && echo 'PASS: upload artifact found in volume' || { echo 'FAIL: upload artifact missing'; exit 1; }
  found_v=\$(find /app/backend/data/vectors -name '${DOC_ID}*' | wc -l)
  [ \"\$found_v\" -ge 1 ] && echo 'PASS: vector artifact found in volume' || { echo 'FAIL: vector artifact missing'; exit 1; }
"

echo ""
echo "=== Step 5: Stop and recreate container on the SAME volume ==="
docker stop "${CONTAINER}"
docker rm "${CONTAINER}"
docker run -d \
  --name "${CONTAINER}" \
  -p "${PORT}:8000" \
  -e PORT=8000 \
  -e HF_HUB_OFFLINE=1 \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HAMIGENZ_SESSION_SECRET="${SESSION_SECRET}" \
  -v "${VOLUME}:/app/backend/data" \
  ${MODEL_CACHE_DIR:+-v "${MODEL_CACHE_DIR}:/app/backend/data/huggingface:ro"} \
  "${IMAGE}"

echo "--- Waiting for /health after restart ---"
for i in $(seq 1 30); do
  if curl -sf "${BASE_URL}/health" > /dev/null; then
    echo "PASS: /health returned 200 after restart (attempt $i)"
    break
  fi
  [ "$i" -eq 30 ] && { echo "ERROR: container did not recover after restart"; docker logs "${CONTAINER}"; exit 1; }
  sleep 2
done

echo ""
echo "=== Step 6: Verify document persisted across restart ==="
VIEWER_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "X-Session-Token: ${SESSION_TOKEN}" \
  "${BASE_URL}/documents/${DOC_ID}/viewer")
[ "${VIEWER_STATUS}" = "200" ] \
  && echo "PASS: document viewer returns 200 after restart (persistence confirmed)" \
  || { echo "FAIL: viewer returned ${VIEWER_STATUS} after restart — data was not persisted"; exit 1; }

echo ""
echo "=== Step 7: Delete document and verify artifacts removed ==="
DEL_RESP=$(curl -sf -X DELETE \
  -H "X-Session-Token: ${SESSION_TOKEN}" \
  "${BASE_URL}/documents/${DOC_ID}")
echo "Delete response: ${DEL_RESP}"
DEL_STATUS=$(echo "${DEL_RESP}" | jq -r '.status')
[ "${DEL_STATUS}" = "deleted" ] && echo "PASS: delete returned status=deleted" || { echo "FAIL: delete did not return status=deleted"; exit 1; }

# Verify physical removal on the volume
docker exec "${CONTAINER}" sh -c "
  found=\$(find /app/backend/data/uploads -name '*${DOC_ID}*' 2>/dev/null | wc -l)
  [ \"\$found\" -eq 0 ] && echo 'PASS: upload artifact removed from volume after delete' || { echo \"FAIL: upload artifact still present (\$found files)\"; exit 1; }
  found_v=\$(find /app/backend/data/vectors -name '${DOC_ID}*' 2>/dev/null | wc -l)
  [ \"\$found_v\" -eq 0 ] && echo 'PASS: vector artifact removed from volume after delete' || { echo \"FAIL: vector artifact still present (\$found_v files)\"; exit 1; }
"

# Verify 404 on viewer after delete
VIEWER_AFTER=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "X-Session-Token: ${SESSION_TOKEN}" \
  "${BASE_URL}/documents/${DOC_ID}/viewer")
[ "${VIEWER_AFTER}" = "404" ] \
  && echo "PASS: viewer returns 404 after delete" \
  || echo "WARNING: viewer returned ${VIEWER_AFTER} after delete (may be cached)"

echo ""
echo "======================================================="
echo "  PASS: Docker named-volume persistence test complete"
echo "======================================================="
