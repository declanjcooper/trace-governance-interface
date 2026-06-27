import streamlit as st
import zipfile
import json

# Configure the Streamlit page layout
st.set_page_config(page_title="TRACE Container Validator", layout="centered")

st.title("TRACE Container Validator")
st.markdown("""
This utility executes a structural validation check on `.docx` containers to establish a deterministic baseline before data extraction.
""")

# File Uploader
uploaded_file = st.file_uploader("Upload a .docx container file", type=["docx"])

if uploaded_file is not None:
    try:
        # Open the uploaded file as a zip archive in memory
        with zipfile.ZipFile(uploaded_file) as z:
            # Gather the comprehensive file list inside the container
            all_files = z.namelist()

            # Define exact structural targets
            must_have_targets = [
                "word/document.xml",
                "docProps/core.xml",
                "_rels/.rels"
            ]

            must_not_have_targets = [
                "word/comments.xml",
                "word/footnotes.xml",
                "word/endnotes.xml",
                "word/revisions.xml"
            ]

            # Execute validation logic matching your JSON output format
            # must_have returns True if present (which is required)
            must_have_results = {target: (target in all_files) for target in must_have_targets}

            # must_not_have returns True if present (which indicates contamination)
            must_not_have_results = {target: (target in all_files) for target in must_not_have_targets}

            # Determine overall verdict based on constraints
            passed_must_have = all(must_have_results.values())
            passed_must_not_have = not any(must_not_have_results.values())

            verdict = "PASS" if (passed_must_have and passed_must_not_have) else "FAIL"

            # Construct the final standardized JSON output
            validation_output = {
                "filename": uploaded_file.name,
                "verdict": verdict,
                "must_have": must_have_results,
                "must_not_have": must_not_have_results,
                "all_files": all_files
            }

            # Display UI Results Panel
            st.subheader("Validation Result")
            if verdict == "PASS":
                st.success(f"Result: {verdict}")
            else:
                st.error(f"Result: {verdict}")

            # Render the raw JSON output exactly as your backend produces it
            st.subheader("JSON Output")
            st.json(validation_output)

    except zipfile.BadZipFile:
        st.error("The uploaded file is not a valid zip archive or .docx container.")
    except Exception as e:
        st.error(f"An unexpected error occurred during processing: {str(e)}")
