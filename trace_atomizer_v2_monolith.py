import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
import io
import json
import pandas as pd
import time

st.set_page_config(page_title="TRACE Monolith V2", layout="wide")

# --- UI TYPOGRAPHY OVERRIDE ---
st.markdown("""
    <style>
    /* Minimal intervention: Upscale caption fonts and darken them */
    small, .stCaption, [data-testid="stCaptionContainer"] {
        font-size: 1rem !important;
        color: #333333 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURATION ---
NAMESPACES = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/package/2006/relationships',
    'ct': 'http://schemas.openxmlformats.org/package/2006/content-types'
}

# --- HEURISTIC ENGINE ---
def guess_atom_type(value):
    val = value.lower().strip()
    if val.startswith(("step", "action")) or "procedure:" in val: return "procedure_step"
    if val.startswith(("role:", "responsibility:")): return "role"
    if val.startswith(("definition:", "term:", "def:")): return "definition"
    if val.startswith(("note:", "warning:", "caution:")) or val.startswith("note "): return "warning"
    return "text"

def guess_context(value, predicted_type):
    val = value.lower()
    if predicted_type == "role" and ":" in value: return "declaration"
    if predicted_type == "procedure_step" and "if" in val: return "conditional"
    return "implicit"

# --- CORE LOGIC ---
def atomize_ooxml(file_buffer):
    telemetry = {"metadata": {}, "atoms": [], "health": "COMPLIANT"}
    try:
        with zipfile.ZipFile(file_buffer, 'r') as docx:
            telemetry["metadata"]["discovered_parts"] = [n for n in docx.namelist() if n.startswith("word/")]
            styles_xml = docx.read('word/styles.xml')
            document_xml = docx.read('word/document.xml')

        styles_root = ET.fromstring(styles_xml)
        doc_root = ET.fromstring(document_xml)

        style_map = {}
        for style in styles_root.findall('.//w:style', NAMESPACES):
            style_id = style.get(f"{{{NAMESPACES['w']}}}styleId")
            name_node = style.find('.//w:name', NAMESPACES)
            if name_node is not None and style_id is not None:
                style_map[style_id] = name_node.get(f"{{{NAMESPACES['w']}}}val").lower()

        body = doc_root.find('.//w:body', NAMESPACES)
        if body is None: raise Exception("Document body not found.")

        atom_counter = 1
        current_heading_id = None

        for element in body:
            if element.tag == f"{{{NAMESPACES['w']}}}p":
                texts = element.findall('.//w:t', NAMESPACES)
                para_text = "".join([t.text for t in texts if t.text]).strip()
                if not para_text: continue

                style_node = element.find('.//w:pPr/w:pStyle', NAMESPACES)
                style_id = style_node.get(f"{{{NAMESPACES['w']}}}val") if style_node is not None else "Normal"
                true_style = style_map.get(style_id, "normal")

                p_type = "heading" if "heading" in true_style else guess_atom_type(para_text)
                if p_type == 'heading': current_heading_id = str(atom_counter)

                telemetry["atoms"].append({
                    "index": str(atom_counter),
                    "type": p_type,
                    "structural_context": guess_context(para_text, p_type),
                    "parent_heading_ref": current_heading_id,
                    "value": para_text,
                    "accountability_reference": "SYSTEM_INGEST_V1"
                })
                atom_counter += 1

            elif element.tag == f"{{{NAMESPACES['w']}}}tbl":
                for row in element.findall('.//w:tr', NAMESPACES):
                    row_data = [ "".join([t.text for t in cell.findall('.//w:t', NAMESPACES) if t.text]).strip()
                                for cell in row.findall('.//w:tc', NAMESPACES) ]
                    if any(row_data):
                        telemetry["atoms"].append({
                            "index": str(atom_counter),
                            "type": "table_row",
                            "structural_context": "grid_data",
                            "parent_heading_ref": current_heading_id,
                            "value": " | ".join(row_data),
                            "accountability_reference": "SYSTEM_INGEST_V1"
                        })
                        atom_counter += 1
        return telemetry
    except Exception as e:
        return {"health": "FRACTURED", "errors": [str(e)], "atoms": []}

# --- UI LOGIC ---
st.title("🧩 TRACE: Integrated Audit Gate")
if "trace_payload" not in st.session_state: st.session_state.trace_payload = None
tab1, tab2, tab3 = st.tabs(["1. Acquisition", "2. Diagnostic & Reconstruction", "3. Synthesis"])

with tab1:
    st.markdown("### Step 1: Ingest Payload")
    if st.session_state.trace_payload: st.success("✅ Payload loaded. Proceed to Diagnostic.")
    uploaded = st.file_uploader("Upload .docx", type=["docx"])
    if uploaded and st.button("Run Acquisition"):
        st.session_state.trace_payload = atomize_ooxml(io.BytesIO(uploaded.read()))
        st.rerun()

with tab2:
    if st.session_state.trace_payload:
        if st.session_state.trace_payload["health"] == "FRACTURED":
            st.error("🚨 Extraction Error:"); st.code(st.session_state.trace_payload.get("errors")); st.stop()
        if not st.session_state.trace_payload.get("atoms"): st.warning("⚠️ No data found."); st.stop()

        st.markdown("### Structural Triage & Live Reconstruction")
        st.info("**Training Objective (The Architectural Auditor):** The engine has mapped the document's lineage. Your task as an Architectural Auditor is to perform deterministic validation. Ensure the structural hierarchy (Parent-Child nodes) aligns with your business logic before finalizing the manifest.")

        col1, col2 = st.columns([1, 1])
        with col1:
            df = pd.DataFrame(st.session_state.trace_payload["atoms"])
            edited_df = st.data_editor(df[["index", "parent_heading_ref", "type", "structural_context", "value"]],
                column_config={"type": st.column_config.SelectboxColumn("Entity Type", options=["text", "heading", "procedure_step", "role", "definition", "warning", "table_row"], required=True),
                               "structural_context": st.column_config.SelectboxColumn("Context", options=["implicit", "declaration", "reference", "conditional", "grid_data"], required=True)},
                width='stretch', hide_index=True, height=500)
            if st.button("Finalize Manifest", type="primary"):
                st.session_state.trace_payload["atoms"] = edited_df.to_dict('records')
                st.session_state.trace_payload["health"] = "COMPLIANT-REMEDIATED"
                st.success("Manifest Locked.")
        with col2:
            st.markdown("#### :material/account_tree: Live Machine View")
            with st.container(height=500):
                for _, row in edited_df.iterrows():
                    badge = f" `[{row['structural_context'].upper()}]`" if row['structural_context'] != 'implicit' else ""
                    tag = f" <small>*(Parent: #{row['parent_heading_ref']})*</small>" if pd.notna(row['parent_heading_ref']) else ""
                    if row['type'] == 'heading': st.markdown(f"### [#{row['index']}] {row['value']}"); st.divider()
                    elif row['type'] == 'procedure_step': st.markdown(f":material/format_list_bulleted: **Step{badge}:** {row['value']}{tag}", unsafe_allow_html=True)
                    elif row['type'] == 'warning': st.error(f":material/warning: **WARNING:** {row['value']}", icon="🚨")
                    elif row['type'] == 'role': st.markdown(f":material/person_check: **Role{badge}:** `{row['value']}`{tag}", unsafe_allow_html=True)
                    elif row['type'] == 'definition': st.info(f":material/menu_book: **Definition:** {row['value']}", icon="ℹ️")
                    elif row['type'] == 'table_row': st.markdown(f":material/table_rows: **Grid Data{badge}:** `{row['value']}`{tag}", unsafe_allow_html=True)
                    else: st.markdown(f"{row['value']}{tag}", unsafe_allow_html=True)
    else: st.warning("⚠️ Waiting for payload.")

with tab3:
    if st.session_state.trace_payload and st.session_state.trace_payload["health"] != "FRACTURED":
        st.json(st.session_state.trace_payload["atoms"])
        st.download_button("Export SSOT Ledger", json.dumps(st.session_state.trace_payload), "ssot_ledger.json")
