import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
import json
import uuid
import pandas as pd
from typing import Dict, Any, List

# ==========================================
# --- TOPOLOGICAL ALIGNMENT CORE ---
# ==========================================
# (Kept separate to ensure SoC)

def generate_dag_vectors(zip_ref: zipfile.ZipFile, filename: str) -> Dict[str, Any]:
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
            "hasChild": []
        }
        node_map[node_id] = node_data
        for child in node:
            child_id = traverse(child, new_path, node_id)
            node_map[node_id]["hasChild"].append(child_id)
        return node_id

    traverse(root, ["Root"], None)
    return node_map

def evaluate_alignment_strain(node_map: Dict[str, Any]) -> Dict[str, Any]:
    for node in node_map.values():
        node["status"] = "Equilibrium"
        # Example Logic: Flagging fragmentation
        if " -> p" in node.get("dag_path", ""):
            text_runs = [c for c in node.get("hasChild", []) if " -> r" in node_map.get(c, {}).get("dag_path", "")]
            if len(text_runs) > 1:
                node["status"] = "Strain"
    return node_map

# ==========================================
# --- PEDAGOGICAL CONTROLLER ---
# ==========================================
class PedagogicalController:
    def __init__(self):
        self.step = 1
        self.steps = {
            1: "Load Template (eCRF)",
            2: "Atomize Document (UKR+ DAG)",
            3: "Alignment Diagnosis (Strain Detection)",
            4: "Reconciliation (The Snap)"
        }

    def next(self):
        if self.step < len(self.steps):
            self.step += 1

    def get_instruction(self):
        return self.steps[self.step]

# ==========================================
# --- UI OBSERVATION LAYER ---
# ==========================================
def main():
    st.set_page_config(page_title="Chestnut Alignment Tour", layout="wide")
    
    # Initialize Controller in Session State
    if 'controller' not in st.session_state:
        st.session_state.controller = PedagogicalController()
    
    controller = st.session_state.controller
    
    st.title("Chestnut Alignment Tour")
    st.sidebar.markdown(f"**Current Lesson:** {controller.get_instruction()}")
    
    # --- Step 1: Template ---
    if controller.step == 1:
        st.header("Step 1: Ingesting the Contract")
        st.write("First, we define the 'Root Note'. Upload your eCRF JSON to define our alignment schema.")
        st.file_uploader("Upload eCRF/Contract Template", type=["json", "pdf"])
        if st.button("Proceed to Mapping"):
            controller.next()
            st.rerun()

    # --- Step 2: Ingestion ---
    elif controller.step == 2:
        st.header("Step 2: Building the Topology")
        st.write("We are converting the physical document into a logical DAG.")
        doc = st.file_uploader("Upload .docx for Atomization", type=["docx"])
        if doc:
            if st.button("Generate DAG"):
                st.session_state.node_map = generate_dag_vectors(zipfile.ZipFile(doc), "word/document.xml")
                controller.next()
                st.rerun()

    # --- Step 3: Strain Detection ---
    elif controller.step == 3:
        st.header("Step 3: Detecting Alignment Strain")
        st.write("We compare the DAG topology against the Contract.")
        node_map = evaluate_alignment_strain(st.session_state.node_map)
        
        strained = [n for n in node_map.values() if n["status"] == "Strain"]
        st.error(f"Detected {len(strained)} nodes in State of Strain.")
        
        if st.button("Resolve (Reconcile)"):
            controller.next()
            st.rerun()

    # --- Step 4: Reconciliation ---
    elif controller.step == 4:
        st.header("Step 4: Reconciliation Complete")
        st.success("The document is now aligned with the contract.")
        if st.button("Restart Tour"):
            st.session_state.controller = PedagogicalController()
            st.rerun()

if __name__ == "__main__":
    main()
        
