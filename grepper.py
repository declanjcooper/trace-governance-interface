import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple

# ==========================================
# --- CONFIGURATION LAYER ---
# ==========================================
APP_TITLE = "Chestnut TRACE Container Validator (Test Mode)"
MAX_CONTEXT_CHARS = 1000

# The Deterministic Baseline ()
# Only these structural components are authorized to exist.
AUTHORIZED_EXACT = {
    "[Content_Types].xml",
    "_rels/.rels",
    "word/_rels/document.xml.rels",
    "word/document.xml",
    "word/styles.xml",
    "word/fontTable.xml",
    "word/settings.xml",
    "word/theme/theme1.xml",
    "word/numbering.xml",
    "docProps/core.xml",
    "docProps/app.xml",
    "docProps/custom.xml"
}

# Dynamic files (like headers, footers, and custom XML bindings)
# that belong to the presentation/structural baseline.
AUTHORIZED_PREFIXES = (
    "word/header",
    "word/footer",
    "customXml/"
)


# ==========================================
# --- DATA EXTRACTION LAYER ---
# ==========================================
def extract_text_context(zip_ref: zipfile.ZipFile, filename: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """
    Parses XML structure to strip all presentation tags.
    If the file is a non-XML binary, it safely bypasses parsing and reports the file footprint.
    """
    try:
        # The Sniff Test: Only parse if it claims to be XML or a relationship map
        if not filename.endswith(('.xml', '.rels')):
            file_info = zip_ref.getinfo(filename)
            return f"[Non-XML Binary Detected: {file_info.file_size} bytes. Extraction bypassed to preserve isolation.]"

        raw_bytes = zip_ref.read(filename)
        root = ET.fromstring(raw_bytes)

        # Strip the XML structure, leaving only the raw data
        text_content = " ".join(root.itertext())
        text_content = " ".join(text_content.split())

        # Accurate reporting
        if not text_content:
            return "[File exists in container, but contains no extractable text]"

        if len(text_content) > max_chars:
            return f"{text_content[:max_chars]}... \n\n[TRUNCATED FOR REVIEW: Limit {max_chars} chars]"

        return text_content

    except ET.ParseError:
        return "[Error: Target structure is corrupted and could not be parsed as valid XML]"
    except Exception as e:
        return f"[Error extracting content: {str(e)}]"


# ==========================================
# --- VALIDATION ENGINE LAYER ---
# ==========================================
def validate_container(uploaded_file) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
    """
    Executes structural validation using a strict Default-Deny Whitelist.
    Returns the verdict, standard output payload, and failure list.
    """
    with zipfile.ZipFile(uploaded_file) as z:
        all_files = set(z.namelist())

        baseline_results = {}
        failures = []

        # Validate against the Strict Whitelist
        for target in all_files:
            # Check if the file is part of the authorized SSOT
            is_authorized = target in AUTHORIZED_EXACT or target.startswith(AUTHORIZED_PREFIXES)
            baseline_results[target] = is_authorized

            if not is_authorized:
                # If it is not explicitly authorized, it is an offender by default.
                extracted_coi = extract_text_context(z, target)

                failures.append({
                    "failure_id": "ERR_UNAUTHORIZED_CONTENT",
                    "target": target,
                    "description": "Unrecognized structural file detected. Extracted for human review.",
                    "context": extracted_coi
                })

        # Evaluate constraints: If any file in the container was unauthorized, the container fails.
        verdict = "PASS" if all(baseline_results.values()) else "FAIL"

        # Construct payload
        output_payload = {
            "filename": uploaded_file.name,
            "verdict": verdict,
            "baseline_validation": baseline_results,
            "failures": failures,
            "all_files": list(all_files)
        }

        return verdict, output_payload, failures


# ==========================================
# --- PRESENTATION LAYER (UI) ---
# ==========================================
def main():
    st.set_page_config(page_title="TRACE Grepper", layout="centered")
    st.title(APP_TITLE)
    st.markdown(
        "This utility executes a structural validation check on `.docx` containers using a **strict whitelist**. "
        "Any file not explicitly required for text rendering is isolated, extracted, and flattened for review."
    )

    uploaded_file = st.file_uploader("Upload a .docx container file", type=["docx"])

    if uploaded_file is not None:
        try:
            # Delegate logic to the Validation Engine
            verdict, output_payload, failures = validate_container(uploaded_file)

            # Render Results Panel
            st.subheader("Validation Result")
            if verdict == "PASS":
                st.success(f"Result: {verdict} — Container matches the authorized baseline.")
            else:
                st.error(f"Result: {verdict} — {len(failures)} unauthorized target(s) detected.")

                for f in failures:
                    st.warning(f"**{f['failure_id']}**: `{f['target']}`")
                    if f['context']:
                        with st.expander(f"Inspect Text Content for {f['target']}"):
                            st.info(f['context'])

            # Render JSON Payload
            st.subheader("JSON Output")
            st.json(output_payload)

        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid zip archive or .docx container.")
        except Exception as e:
            st.error(f"An unexpected error occurred during processing: {str(e)}")


if __name__ == "__main__":
    main()
