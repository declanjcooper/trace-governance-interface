import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Tuple

# ==========================================
# --- CONFIGURATION LAYER ---
# ==========================================
APP_TITLE = "Chestnut TRACE Container Validator"
MAX_CONTEXT_CHARS = 1000

# Using sets for O(1) membership lookups
MUST_HAVE_TARGETS = {
    "word/document.xml",
    "docProps/core.xml",
    "_rels/.rels"
}

MUST_NOT_HAVE_TARGETS = {
    "word/comments.xml",
    "word/footnotes.xml",
    "word/endnotes.xml",
    "word/revisions.xml"
}


# ==========================================
# --- DATA EXTRACTION LAYER ---
# ==========================================
def extract_text_context(zip_ref: zipfile.ZipFile, filename: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """
    Parses XML structure to strip tags and returns normalized, human-readable text.
    """
    try:
        raw_bytes = zip_ref.read(filename)
        root = ET.fromstring(raw_bytes)

        # Extract and normalize text spacing
        text_content = " ".join(root.itertext())
        text_content = " ".join(text_content.split())

        if not text_content:
            return "[No readable text content found]"

        if len(text_content) > max_chars:
            return f"{text_content[:max_chars]}... [Truncated at {max_chars} characters]"

        return text_content

    except ET.ParseError:
        return "[Error: Target is not valid XML or could not be parsed]"
    except Exception as e:
        return f"[Error extracting content: {str(e)}]"


# ==========================================
# --- VALIDATION ENGINE LAYER ---
# ==========================================
def validate_container(uploaded_file) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
    """
    Executes structural validation against defined constraints.
    Returns the verdict, standard output payload, and failure list.
    """
    with zipfile.ZipFile(uploaded_file) as z:
        # Cast to set for faster membership checking
        all_files = set(z.namelist())

        must_have_results = {}
        must_not_have_results = {}
        failures = []

        # Validate Required Targets
        for target in MUST_HAVE_TARGETS:
            is_present = target in all_files
            must_have_results[target] = is_present

            if not is_present:
                failures.append({
                    "failure_id": "ERR_MISSING_REQUIRED",
                    "target": target,
                    "description": "Required structural file is missing.",
                    "context": None
                })

        # Validate Prohibited Targets
        for target in MUST_NOT_HAVE_TARGETS:
            is_present = target in all_files
            must_not_have_results[target] = is_present

            if is_present:
                failures.append({
                    "failure_id": "ERR_UNAUTHORIZED_CONTENT",
                    "target": target,
                    "description": "Container contamination detected.",
                    "context": extract_text_context(z, target)
                })

        # Evaluate constraints
        passed_must_have = all(must_have_results.values())
        passed_must_not_have = not any(must_not_have_results.values())
        verdict = "PASS" if (passed_must_have and passed_must_not_have) else "FAIL"

        # Construct payload
        output_payload = {
            "filename": uploaded_file.name,
            "verdict": verdict,
            "must_have": must_have_results,
            "must_not_have": must_not_have_results,
            "failures": failures,
            "all_files": list(all_files) # Converted back to list for JSON serialization
        }

        return verdict, output_payload, failures


# ==========================================
# --- PRESENTATION LAYER (UI) ---
# ==========================================
def main():
    st.set_page_config(page_title="XML Grepper", layout="centered")
    st.title(APP_TITLE)
    st.markdown(
        "This utility executes a structural validation check on `.docx` containers to "
        "establish a deterministic baseline before data extraction."
    )

    uploaded_file = st.file_uploader("Upload a .docx container file", type=["docx"])

    if uploaded_file is not None:
        try:
            # Delegate logic to the Validation Engine
            verdict, output_payload, failures = validate_container(uploaded_file)

            # Render Results Panel
            st.subheader("Validation Result")
            if verdict == "PASS":
                st.success(f"Result: {verdict}")
            else:
                st.error(f"Result: {verdict} — {len(failures)} issue(s) detected.")

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
