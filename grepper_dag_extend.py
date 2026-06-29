import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
import json
import uuid
from typing import Dict, Any, List, Tuple

# ==========================================
# --- CORE ENGINE v2.1 ---
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
    raw_bytes = zip_ref.read(filename)
    root = ET.fromstring(raw_bytes)
    node_map, exceptions = {}, []

    def traverse(node, current_path, parent_id):
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        tag_name = node.tag.split('}')[-1]
        new_path = current_path + [tag_name]

        if tag_name not in ['body', 'p', 'r', 't', 'tbl', 'tr', 'tc', 'document']:
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

        node_map[node_id] = node_map.get(node_id, {})
        node_map[node_id].update(node_data)

        for child in node:
            child_id = traverse(child, new_path, node_id)
            node_map[node_id]["hasChild"].append(child_id)

        return node_id

    traverse(root, ["Root"], None)
    return node_map, exceptions

# ==========================================
# --- PRESENTATION LAYER ---
# ==========================================
def main():
    st.set_page_config(page_title="Chestnut Compiler", layout="wide")
    st.title("Chestnut TRACE Compiler")

    uploaded_file = st.file_uploader("Upload .docx for Deterministic Archive", type=["docx"])

    if uploaded_file:
        with zipfile.ZipFile(uploaded_file) as z:
            node_map, exceptions = generate_dag_vectors(z, "word/document.xml")

            # --- UI Interrogation ---
            st.subheader("Interrogation Station")
            col1, col2 = st.columns(2)
            search_path = col1.text_input("Grep Path (e.g., 'tbl')", "")

            if search_path:
                matches = [n for n in node_map.values() if search_path in n.get('dag_path', '')]
                col2.write(f"Found {len(matches)} nodes.")
                st.table([{"ID": m["@id"], "Path": m["dag_path"], "Content": m.get("coi", "")} for m in matches])

            # --- Downloads ---
            json_ld = json.dumps({"@context": TRACE_CONTEXT, "trace:extractedData": list(node_map.values())}, indent=2)
            st.download_button("⬇️ Download miniPACS JSON-LD", json_ld, file_name="TRACE_Archive.jsonld")

if __name__ == "__main__":
    main()
