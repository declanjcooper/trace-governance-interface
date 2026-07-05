import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
import json
import uuid
import pandas as pd
from typing import Dict, Any, List, Tuple

# ==========================================
# --- TOPOLOGICAL ALIGNMENT CORE v2.2 ---
# ==========================================
TRACE_CONTEXT = {
    "trace": "https://schema.chestnut-architecture.dev/trace/v2#",
    "dag_path": "trace:hasCoordinatePath",
    "coi": "trace:hasContentOfInterest",
    "depth": "trace:hasTopologicalDepth",
    "parent": "trace:hasParentNode",
    "hasChild": {"@id": "trace:hasChildNode", "@container": "@set"}
}

def generate_dag_vectors(zip_ref: zipfile.ZipFile, filename: str) -> Tuple[Dict[str, Any], List[str]]:
    """Ingests XML and atomizes into the UKR+ topological DAG."""
    raw_bytes = zip_ref.read(filename)
    root = ET.fromstring(raw_bytes)
    node_map, exceptions = {}, []

    def traverse(node, current_path, parent_id):
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        tag_name = node.tag.split('}')[-1]
        new_path = current_path + [tag_name]

        # Log anomalies in the structure
        if tag_name not in ['body', 'p', 'r', 't', 'tbl', 'tr', 'tc', 'document', 'pPr', 'rPr', 'b', 'bCs', 'sectPr', 'pgSz', 'pgMar', 'cols', 'docGrid']:
            exceptions.append(f"Anomalous Tag: {tag_name} at {'->'.join(new_path)}")

        node_data = {
            "@id": node_id,
            "@type": "TopologicalNode",
            "dag_path": " -> ".join(new_path),
            "depth": len(new_path),
            "parent": parent_id,
            "hasChild": []
        }
        if node.text and node.text.strip():
            node_data["coi"] = node.text.strip()

        node_map[node_id] = node_data

        for child in node:
            child_id = traverse(child, new_path, node_id)
            node_map[node_id]["hasChild"].append(child_id)

        return node_id

    traverse(root, ["Root"], None)
    return node_map, exceptions

def evaluate_alignment_strain(node_map: Dict[str, Any]) -> Dict[str, Any]:
    """
    Contract Physics Engine: Evaluates data alignment against compliance vectors.
    """
    for node_id, node in node_map.items():
        node["alignment_status"] = "Equilibrium"
        node["alignment_notes"] = []

        # 1. Alignment Check: Topological Fragmentation
        # If a paragraph (p) contains multiple text runs, it indicates a lack of semantic atomization.
        if " -> p" in node.get("dag_path", ""):
            text_runs = [c for c in node.get("hasChild", []) if " -> r" in node_map.get(c, {}).get("dag_path", "")]
            if len(text_runs) > 1:
                node["alignment_status"] = "Strain"
                node["alignment_notes"].append(f"Fragmentation: {len(text_runs)} text runs detected.")

        # 2. Alignment Check: Governance Contract Violation
        # If run properties (rPr) contains 'b' (bold), it violates the master style contract.
        if " -> rPr" in node.get("dag_path", ""):
            if any(" -> b" in node_map.get(c, {}).get("dag_path", "") for c in node.get("hasChild", [])):
                node["alignment_status"] = "Strain"
                node["alignment_notes"].append("Contract Violation: Unauthorized Direct Formatting.")
                
    return node_map

# ==========================================
# --- PRESENTATION LAYER ---
# ==========================================
def main():
    st.set_page_config(page_title="Chestnut Alignment Core", layout="wide")
    st.title("Chestnut Topological Alignment Core")
    st.markdown("### Deterministic Alignment & Contract Physics Observation")

    uploaded_file = st.file_uploader("Upload .docx for Deterministic Archive", type=["docx"])

    if uploaded_file:
        with zipfile.ZipFile(uploaded_file) as z:
            # 1. Ingestion / Atomization
            node_map, exceptions = generate_dag_vectors(z, "word/document.xml")
            
            # 2. Alignment Evaluation
            node_map = evaluate_alignment_strain(node_map)

            # --- UI Interrogation ---
            st.subheader("Interrogation Station")
            col1, col2 = st.columns([1, 2])
            search_path = col1.text_input("Grep Coordinate Path (e.g., 'body -> p')", "")

            # --- Alignment Observation UI ---
            st.subheader("Observability: Equilibrium vs. Strain")
            
            # Prepare DataFrame
            df_data = []
            for n in node_map.values():
                df_data.append({
                    "ID": n["@id"], 
                    "Path": n["dag_path"], 
                    "Status": n["alignment_status"], 
                    "Notes": "; ".join(n["alignment_notes"]) if n["alignment_notes"] else "None"
                })
            
            df = pd.DataFrame(df_data)

            # Conditional formatting for "Strain"
            def highlight_status(s):
                return ['background-color: #ffcccc' if x == 'Strain' else 'background-color: #ccffcc' for x in s]

            # Filtering logic
            if search_path:
                df = df[df['Path'].str.contains(search_path, na=False)]
            
            st.dataframe(df.style.apply(highlight_status, subset=['Status']), use_container_width=True)

            # --- Downloads ---
            json_ld = json.dumps({"@context": TRACE_CONTEXT, 
                                  "trace:extractedData": list(node_map.values())}, indent=2)
            st.download_button("⬇️ Download miniPACS JSON-LD", json_ld, file_name="TRACE_Archive.jsonld")

            if exceptions:
                with st.expander("View Structural Anomalies"):
                    st.write(exceptions)

if __name__ == "__main__":
    main()
