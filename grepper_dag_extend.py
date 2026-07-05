import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
import json
import uuid
import pandas as pd
from typing import Dict, Any

# ==========================================
# --- TOPOLOGICAL ALIGNMENT CORE ---
# ==========================================

def generate_dag_vectors(zip_ref: zipfile.ZipFile, filename: str) -> Dict[str, Any]:
    """Ingests XML and atomizes into the UKR+ topological DAG."""
    try:
        raw_bytes = zip_ref.read(filename)
        root = ET.fromstring(raw_bytes)
        node_map = {}

        def traverse(node, current_path, parent_id):
            node_id = f"node_{uuid.uuid4().hex[:8]}"
            tag_name = node.tag.split('}')[-1]
            new_path = current_path + [tag_name]
            
            node_data = {
                "@id": node_id,
                "dag_path": " -> ".join(new_path),
                "coi": node.text.strip() if node.text and node.text.strip() else None,
                "parent": parent_id,
                "hasChild": []
            }
            node_map[node_id] = node_data
            for child in node:
                child_id = traverse(child, new_path, node_id)
                node_map[node_id]["hasChild"].append(child_id)
            return node_id

        traverse(root, ["Root"], None)
        return node_map
    except Exception as e:
        st.error(f"Ingestion Error: {e}")
        return {}

def evaluate_alignment_strain(node_map: Dict[str, Any]) -> Dict[str, Any]:
    """Applies Contract Physics to the DAG."""
    for node in node_map.values():
        node["status"] = "Equilibrium"
        node["notes"] = []
        if " -> p" in node.get("dag_path", ""):
            text_runs = [c for c in node.get("hasChild", []) if " -> r" in node_map.get(c, {}).get("dag_path", "")]
            if len(text_runs) > 1:
                node["status"] = "Strain"
                node["notes"].append("Fragmentation detected")
    return node_map

# ==========================================
# --- PEDAGOGICAL CONTROLLER ---
# ==========================================
class PedagogicalController:
    def __init__(self):
        self.step = 1
        self.steps = {1: "Initialize Contract", 2: "Atomize Topology", 3: "Alignment Diagnosis"}

    def get_instruction(self):
        return self.steps.get(self.step, "Complete")

# ==========================================
# --- UI OBSERVATION LAYER ---
# ==========================================
def main():
    st.set_page_config(page_title="Chestnut Alignment Core", layout="wide")
    st.title("Chestnut Topological Alignment Core")
    
    if 'controller' not in st.session_state:
        st.session_state.controller = PedagogicalController()
    
    # 1. Pipeline Input
    uploaded_file = st.sidebar.file_uploader("Upload .docx", type=["docx"])
    
    if uploaded_file and 'node_map' not in st.session_state:
        with zipfile.ZipFile(uploaded_file) as z:
            st.session_state.node_map = evaluate_alignment_strain(generate_dag_vectors(z, "word/document.xml"))

    # 2. Node Inspector (The "Node Windows")
    if 'node_map' in st.session_state:
        st.subheader("Node Inspector")
        col1, col2 = st.columns([1, 3])
        
        # Select Node to verify
        node_ids = list(st.session_state.node_map.keys())
        selected_id = col1.selectbox("Inspect Node ID", node_ids)
        
        # Display Window
        node_details = st.session_state.node_map[selected_id]
        col2.json(node_details)
        
        # 3. Overview Table
        st.subheader("Observability: Topology Matrix")
        df = pd.DataFrame([{"ID": k, **v} for k, v in st.session_state.node_map.items()])
        st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
    
