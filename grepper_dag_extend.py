import streamlit as st
import zipfile
import xml.etree.ElementTree as ET
import uuid
import datetime
import time
import altair as alt
import pandas as pd
from typing import Dict, Any

# ==========================================
# --- STREAMLIT LIFECYCLE INITIALIZATION ---
# ==========================================
# MUST be at the absolute top of the global scope to prevent lifecycle errors.
st.set_page_config(page_title="Chestnut Alignment Core", layout="wide", initial_sidebar_state="expanded")

def trigger_rerun():
    """Environment-safe rerun handler."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ==========================================
# --- TOPOLOGICAL ALIGNMENT CORE ---
# ==========================================
CONTRACT_REFERENCE = {
    "target_node": "p",
    "required_properties": ["coi", "hasChild"],
    "max_text_runs": 1, 
    "allowed_formatting": ["regular"] 
}

def generate_dag_vectors(zip_ref: zipfile.ZipFile, filename: str) -> Dict[str, Any]:
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
    for node in node_map.values():
        node["alignment_status"] = "Equilibrium"
        node["strain_distance_delta"] = 0  
        node["strain_vectors"] = {} 
        node["alignment_notes"] = []
        
        # Ensure we only evaluate nodes that are part of the paragraph structure
        if " -> p" in node.get("dag_path", ""):
            # Re-establishing the run count logic with explicit list building to avoid syntax errors
            child_ids = node.get("hasChild", [])
            text_runs = []
            for c_id in child_ids:
                if " -> r" in node_map.get(c_id, {}).get("dag_path", ""):
                    text_runs.append(c_id)
            
            run_count = len(text_runs)
            allowed_runs = CONTRACT_REFERENCE["max_text_runs"]
            
            if run_count > allowed_runs:
                delta = run_count - allowed_runs
                node["alignment_status"] = "Strain"
                node["strain_distance_delta"] = delta
                node["strain_vectors"]["y_axis_hierarchy"] = -delta 
                node["alignment_notes"].append(f"Fragmentation: |Δ| = {delta} ({run_count} runs observed vs {allowed_runs} allowed).")
                
    return node_map
