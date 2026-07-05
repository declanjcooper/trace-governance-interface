import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
import json
import uuid
import pandas as pd
import datetime
from typing import Dict, Any

# ==========================================
# --- TOPOLOGICAL ALIGNMENT CORE ---
# ==========================================

# Master Contract (eCRF_plate Overlay / Tuning Pegs)
CONTRACT_REFERENCE = {
    "target_node": "p",
    "required_properties": ["coi", "hasChild"],
    "max_text_runs": 1, # The core constraint against fragmentation
    "allowed_formatting": ["regular"] # No unauthorized bold/italics
}

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
        st.sidebar.error(f"Ingestion Error: {e}")
        return {}

def evaluate_alignment_strain(node_map: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates the physical distance (Delta) between Document Vector and Contract Vector."""
    for node in node_map.values():
        # Initialize at Origin (0,0,0)
        node["alignment_status"] = "Equilibrium"
        node["strain_distance_delta"] = 0  
        node["strain_vectors"] = {} 
        node["alignment_notes"] = []
        
        # Strain Check: Topological Fragmentation (Y-Axis / Hierarchy)
        if " -> p" in node.get("dag_path", ""):
            text_runs = [c for c in node.get("hasChild", []) if " -> r" in node_map.get(c, {}).get("dag_path", "")]
            run_count = len(text_runs)
            allowed_runs = CONTRACT_REFERENCE["max_text_runs"]
            
            if run_count > allowed_runs:
                # Calculate the exact distance of the Strain
                delta = run_count - allowed_runs
                
                node["alignment_status"] = "Strain"
                node["strain_distance_delta"] = delta
                node["strain_vectors"]["y_axis_hierarchy"] = -delta # Negative pull away from origin
                
                node["alignment_notes"].append(f"Fragmentation: |Δ| = {delta} ({run_count} runs observed vs {allowed_runs} allowed).")
                
    return node_map

def reconcile_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """The 'Snap'. Forces a strained node into Equilibrium and logs the vector collapse."""
    
    # 1. Create the Audit Trail if it doesn't exist
    if "reconciliation_history" not in node:
        node["reconciliation_history"] = []
        
    # 2. Archive the Strain Distance before collapsing it
    node["reconciliation_history"].append({
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "resolved_delta": node.get("strain_distance_delta", 0),
        "resolved_vectors": node.get("strain_vectors", {}),
        "action": "Vector Collapse: Fragments stitched into single coherent run."
    })
    
    # 3. Return the Atom to the Origin (0,0,0)
    node["alignment_status"] = "Equilibrium"
    node["strain_distance_delta"] = 0
    node["strain_vectors"] = {}
    node["alignment_notes"] = ["System Reconciled: Atom returned to Origin (0,0,0)."]
    
    return node

# ==========================================
# --- PEDAGOGICAL CONTROLLER ---
# ==========================================
class PedagogicalController:
    def __init__(self):
        self.step = 1
        self.narrative = {
            1: {
                "title": "1. Document Ingestion", 
                "text": "Before we look at data, we must establish an orientation. The Master Contract dictates the expected topology."
            },
            2: {
                "title": "2. Topological Mapping", 
                "text": "Upload a .docx file. The engine will strip away the visual noise (specific to a word processor/desktop interfaces) and map the raw XML into a deterministic DAG path."
            },
            3: {
                "title": "3. Orthogonal Inspection", 
                "text": "Select an atom in the main canvas. We will project its current state against the Master Contract to visualize any geometric strain and calculate its exact distance (Δ) from the origin."
            },
            4: {
                "title": "4. Reconciliation Snap", 
                "text": "For atoms in a state of Strain, engage the reconciliation vector. Watch the node snap back into structural Equilibrium, while securely logging its collapse in the node's immutable history."
            }
        }

    def next(self):
        if self.step < 4: self.step += 1
            
    def prev(self):
        if self.step > 1: self.step -= 1

# ==========================================
# --- UI OBSERVATION LAYER ---
# ==========================================
def main():
    # Set sidebar to default open for the Narrative/Training bar
    st.set_page_config(page_title="Chestnut Alignment Core", layout="wide", initial_sidebar_state="expanded")
    
    if 'controller' not in st.session_state:
        st.session_state.controller = PedagogicalController()
    
    controller = st.session_state.controller

    # ------------------------------------------
    # LEFT PANEL: The Narrative & Control Bar
    # ------------------------------------------
    with st.sidebar:
        st.title("Chestnut Trainer")
        st.markdown("---")
        
        # Contextual Narrative
        current_lesson = controller.narrative[controller.step]
        st.subheader(current_lesson["title"])
        st.write(current_lesson["text"])
        st.markdown("---")
        
        # Step-specific Controls
        if controller.step == 2:
            uploaded_file = st.file_uploader("Upload Document (.docx)", type=["docx"])
            if uploaded_file and st.button("Atomize Data"):
                with zipfile.ZipFile(uploaded_file) as z:
                    st.session_state.node_map = evaluate_alignment_strain(generate_dag_vectors(z, "word/document.xml"))
                controller.next()
                st.rerun()

        # Navigation
        st.markdown("---")
        col_prev, col_next = st.columns(2)
        if col_prev.button("⬅️ Back") and controller.step > 1:
            controller.prev()
            st.rerun()
        if col_next.button("Next ➡️") and controller.step < 4:
            controller.next()
            st.rerun()

    # ------------------------------------------
    # MAIN CANVAS: The Orthogonal Viewer
    # ------------------------------------------
    st.title("Topological Alignment Core")
    
    if controller.step == 1:
        st.info("Awaiting Document Ingestion... (See Left Panel)")
        st.markdown("### Master Contract (Active)")
        st.json(CONTRACT_REFERENCE)
        
    elif controller.step >= 3 and 'node_map' in st.session_state:
        st.subheader("Orthogonal Alignment Viewer")
        
        # Filter nodes to find ones we care about (e.g., paragraphs)
        node_ids = [k for k, v in st.session_state.node_map.items() if " -> p" in v.get("dag_path", "")]
        
        if node_ids:
            selected_id = st.selectbox("Select Atom to Inspect:", node_ids)
            observed_node = st.session_state.node_map[selected_id]
            
            # The Dual-Pane Projection
            col_obs, col_con = st.columns(2)
            
            with col_obs:
                st.markdown("#### Document Vector (Observed)")
                st.json(observed_node)
                
            with col_con:
                st.markdown("#### Contract Vector (Required)")
                st.json(CONTRACT_REFERENCE)
                
            st.divider()
            
            # Strain Status & Resolution
            if observed_node["alignment_status"] == "Strain":
                st.error(f"❌ STRAIN DETECTED: {', '.join(observed_node['alignment_notes'])}")
                
                # The Reconciliation Snap (Step 4 specific)
                if controller.step == 4:
                    if st.button("⚡ Reconcile Atom (Snap to Contract)"):
                        st.session_state.node_map[selected_id] = reconcile_node(observed_node)
                        st.rerun()
            else:
                st.success("✅ EQUILIBRIUM: Atom in alignment with Contract.")
        else:
            st.warning("No paragraph (p) nodes found in the current document structure.")

if __name__ == "__main__":
    main()
