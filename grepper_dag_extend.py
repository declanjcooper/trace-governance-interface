"""
Chestnut TRACE: Comparative Governance Engine (v5.0.2 - SIMD Vectorized Multi-Stream Edition)
Adaptive Multi-Persona Governance Engine with Parameterized Node Coalescing,
Explicit Tabular Matrix Coordinates, Atom Boundary Repair, Clean Vector Text Streams,
Section-Scoped Subtree Remediation, Multi-Part Document Ingestion, Downstream Post-Quarantine Rendering,
& SIMD-Accelerated Parallel Stream C (Provenance & Revision Auditor).
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, List, Optional, Tuple
import zipfile

import altair as alt
import lxml.etree as ET
import numpy as np
import pandas as pd
import streamlit as st

# WordprocessingML Namespace Constants
NS_W: str = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_MAP: Dict[str, str] = {"w": NS_W}

TRANSIENT_TAGS: set[str] = {
    "smartTag",
    "hyperlink",
    "bookmarkStart",
    "bookmarkEnd",
    "proofErr",
    "permStart",
    "permEnd",
}


@dataclass
class StyleDisplacementVector:
    """Calculates geometric style displacement (ΔDt) relative to the Normal Text origin."""
    size_offset_pt: float = 0.0
    weight_delta: int = 0  # 0: normal, 1: bold
    italic_delta: int = 0  # 0: regular, 1: italic
    is_custom_style: bool = False

    def magnitude(self) -> float:
        """Returns the Euclidean displacement distance from Normal Text (0,0,0,0)."""
        return float(
            np.sqrt(
                (self.size_offset_pt / 2.0) ** 2
                + (self.weight_delta * 1.5) ** 2
                + (self.italic_delta * 1.0) ** 2
                + (2.0 if self.is_custom_style else 0.0)
            )
        )


@dataclass
class ChestnutNode:
    """DAG Node representing an OOXML structural element with Explicit Tabular Geometry & Metadata."""

    node_id: str
    dewey_id: str              # Full absolute coordinate or local relative delta string
    delta_dewey: str            # Relative offset from preceding anchor
    tag: str
    path: str
    normalized_path: str
    text: str = ""
    clean_text: str = ""        # Vector-friendly text without formatting noise/leader dots
    style_id: str = "Normal"
    depth: int = 0              # Structural distance (ΔDs) from origin
    in_table: bool = False
    in_textbox: bool = False
    
    # Explicit Tabular & Layout Geometry Metadata
    row_index: Optional[int] = None
    column_index: Optional[int] = None
    is_header_cell: bool = False
    header_for: List[str] = field(default_factory=list)
    grid_span: int = 1
    has_virtual_tab: bool = False
    
    # Inferred/Extracted Metadata Tags
    inferred_category: Optional[str] = None
    extracted_dates: List[str] = field(default_factory=list)
    
    # Provenance & Revision Tracking Attributes (Stream C)
    provenance_state: str = "AI_GENERATED"  # AI_GENERATED, AI_EDITED_HUMAN_REVIEWED, HUMAN_EDITED
    originator: str = "AI_Assistant"
    editor: Optional[str] = None
    approver: Optional[str] = None
    revision_timestamp: Optional[str] = None
    has_human_edits: bool = False

    style_vector: StyleDisplacementVector = field(default_factory=StyleDisplacementVector)
    parent_id: Optional[str] = None
    children: List["ChestnutNode"] = field(default_factory=list)

    def get_coordinate_vector(self) -> np.ndarray:
        """Constructs a deterministic vector combining depth, parity, and style displacement."""
        is_leaf: float = 1.0 if not self.children else 0.0
        return np.array(
            [
                float(self.depth),                                   # ΔDs (Structural Distance)
                -1.0 if (self.in_table or self.in_textbox) else 1.0, # Topological Parity ΔDp
                self.style_vector.magnitude(),                       # ΔDt (Style Displacement)
                is_leaf,
            ],
            dtype=np.float64,
        )


class ResolutionMatrix:
    """Observation Operator resolving XML lineage, styles, and vector anomalies into TRACE States."""

    ANOMALY_TRIGGERS: set[str] = {
        "medidata", "rave", "study inactivation", "crf", "clinical trial",
        "protocol amendment", "sap_v", "inactivation"
    }

    def collapse(
        self, node: ChestnutNode, max_style_delta_threshold: float = 6.0
    ) -> Tuple[str, float, str]:
        style_lower: str = node.style_id.lower()
        path_lower: str = node.normalized_path.lower()
        text_lower: str = node.text.lower()

        # 1. Semantic Anomaly Check (ΔDm) — High-priority Quarantine
        for trigger in self.ANOMALY_TRIGGERS:
            if trigger in text_lower:
                query = f"MATCH (n) WHERE toLower(n.text) CONTAINS '{trigger}' SET n.state = 'Quarantined'"
                return "Quarantined", 0.9900, query

        # 2. Native Headings — Intended Displacements
        if any(h in style_lower for h in ["heading", "title", "subtitle"]):
            query = "MATCH (n) WHERE toLower(n.style) CONTAINS 'heading' SET n.state = 'Native_Heading'"
            return "Native_Heading", 0.9500, query

        # 3. Native Tabular / Virtual Layout Grid
        if node.in_table or node.has_virtual_tab:
            query = "MATCH (n) WHERE n.in_table = true OR n.has_virtual_tab = true SET n.state = 'Native_Tabular'"
            return "Native_Tabular", 0.9436, query

        # 4. Extreme Style Displacement Quarantine (ΔDt)
        if node.style_vector.magnitude() > max_style_delta_threshold:
            query = f"MATCH (n) WHERE n.styleDelta > {max_style_delta_threshold} SET n.state = 'Quarantined'"
            return "Quarantined", 0.9200, query

        # 5. Auxiliary Container Catch-All
        is_auxiliary: bool = (
            node.in_textbox
            or any(seg in path_lower for seg in ["header", "footer", "frame", "sidebar"])
            or any(
                kw in style_lower
                for kw in ["callout", "sidebar", "annotation", "comment", "frame", "caption"]
            )
        )
        if is_auxiliary:
            query = "MATCH (n) WHERE n.in_textbox = true OR n.path CONTAINS 'auxiliary' SET n.state = 'Auxiliary_Container'"
            return "Auxiliary_Container", 0.9100, query

        # 6. Native Body Prose Default
        query = "MATCH (n) SET n.state = 'Native_Prose'"
        return "Native_Prose", 0.8750, query


# --- MIMD Parallel Execution Engine Streams ---


class ContentWorkerStreamA:
    """Stream A Worker: Instruction set focused strictly on precise OOXML text extraction, tab delimiters, & token hygiene."""

    @staticmethod
    def _clean_formatting_noise(text: str) -> str:
        cleaned = re.sub(r"[\.…\.]{2,}", " ", text)
        cleaned = re.sub(r"[ \r\n\f\v]+", " ", cleaned)
        return cleaned.strip()

    def process(self, root_elem: ET._Element) -> Dict[str, Dict[str, str]]:
        content_map = {}

        def _traverse_content(elem: ET._Element, path_id: str):
            tag = elem.tag.split("}")[-1] if isinstance(elem.tag, str) else ""
            
            raw_text = ""
            if tag == "tab":
                raw_text = "\t"
            elif tag == "t":
                raw_text = elem.text or ""

            clean_text = self._clean_formatting_noise(raw_text)
            content_map[path_id] = {
                "raw_text": raw_text,
                "clean_text": clean_text
            }

            child_counter = 1
            for child in elem:
                if isinstance(child.tag, str):
                    _traverse_content(child, f"{path_id}.{child_counter}")
                    child_counter += 1

        _traverse_content(root_elem, "1")
        return content_map


class TopologyWorkerStreamB:
    """Stream B Worker: Instruction set focused strictly on Dewey coordinates, XML DOM paths, & layout geometry."""

    DATE_PATTERN: re.Pattern = re.compile(
        r"\b(?:\d{1,2}/\d{1,2}/\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2})\b",
        re.IGNORECASE,
    )

    def process(self, root_elem: ET._Element, styles_map: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        topology_map = {}

        def _traverse_topology(
            elem: ET._Element,
            dewey_id: str,
            current_path: str,
            depth: int,
            inherited_style: str = "Normal",
            in_table: bool = False,
            in_textbox: bool = False,
            row_idx: Optional[int] = None,
            col_idx: Optional[int] = None,
        ):
            tag = elem.tag.split("}")[-1] if isinstance(elem.tag, str) else ""

            if tag == "tbl":
                in_table = True
            elif tag == "txbxContent":
                in_textbox = True

            node_style = inherited_style
            if tag == "p":
                p_style = elem.find("w:pPr/w:pStyle", NS_MAP)
                if p_style is not None:
                    val = p_style.get(f"{{{NS_W}}}val")
                    if val:
                        node_style = val

            resolved_style = styles_map.get(node_style, node_style)
            raw_path = f"{current_path}/{tag}" if current_path else tag
            path_segments = [seg for seg in raw_path.split("/") if seg not in TRANSIENT_TAGS]
            normalized_path = "/".join(path_segments)

            has_tab = False
            if tag == "r" and elem.find("w:tab", NS_MAP) is not None:
                has_tab = True

            is_header = False
            grid_span = 1
            if tag == "tr":
                trPr = elem.find("w:trPr", NS_MAP)
                if trPr is not None and trPr.find("w:tblHeader", NS_MAP) is not None:
                    is_header = True
            elif tag == "tc":
                tcPr = elem.find("w:tcPr", NS_MAP)
                if tcPr is not None:
                    gs = tcPr.find("w:gridSpan", NS_MAP)
                    if gs is not None:
                        val = gs.get(f"{{{NS_W}}}val")
                        if val and val.isdigit():
                            grid_span = int(val)

            topology_map[dewey_id] = {
                "tag": tag,
                "path": raw_path,
                "normalized_path": normalized_path,
                "style_id": resolved_style,
                "depth": depth,
                "in_table": in_table,
                "in_textbox": in_textbox,
                "row_index": row_idx,
                "column_index": col_idx,
                "is_header": is_header,
                "grid_span": grid_span,
                "has_virtual_tab": has_tab,
            }

            child_counter = 1
            tr_count = 0
            for child in elem:
                if isinstance(child.tag, str):
                    child_tag = child.tag.split("}")[-1]
                    child_dewey = f"{dewey_id}.{child_counter}"
                    
                    next_row_idx = row_idx
                    next_col_idx = col_idx
                    
                    if tag == "tbl" and child_tag == "tr":
                        tr_count += 1
                        next_row_idx = tr_count
                    elif tag == "tr" and child_tag == "tc":
                        next_col_idx = (next_col_idx or 0) + 1

                    _traverse_topology(
                        child,
                        child_dewey,
                        current_path=raw_path,
                        depth=depth + 1,
                        inherited_style=node_style,
                        in_table=in_table,
                        in_textbox=in_textbox,
                        row_idx=next_row_idx,
                        col_idx=next_col_idx,
                    )
                    child_counter += 1

        _traverse_topology(root_elem, "1", "", 0)
        return topology_map


class ProvenanceWorkerStreamC:
    """Stream C SIMD-Accelerated Worker: Instruction set focused on parallel chunk scanning of revision metadata, w:ins, w:del, & author provenance tags."""

    @staticmethod
    def process_vectorized_bytes(xml_bytes: bytes) -> Dict[str, Dict[str, Any]]:
        """Simulates SIMD vector-chunk byte scanning over raw OOXML package bytes for rapid revision extraction."""
        provenance_map = {}
        
        # Fast regex-based byte chunk index tape simulation for high-throughput metadata extraction
        chunk_size = 64
        total_len = len(xml_bytes)
        
        # Vectorized pattern lookups for insertions, deletions, and authorship tags
        ins_matches = list(re.finditer(b'<w:ins\b([^>]*)>', xml_bytes))
        del_matches = list(re.finditer(b'<w:del\b([^>]*)>', xml_bytes))
        
        # Map indices or paths to provenance attributes
        for match in ins_matches:
            attrs = match.group(1).decode('utf-8', errors='ignore')
            author_match = re.search(r'w:author="([^"]+)"', attrs)
            date_match = re.search(r'w:date="([^"]+)"', attrs)
            
            author = author_match.group(1) if author_match else "Unknown_Editor"
            timestamp = date_match.group(1) if date_match else None
            
            # Record positional signature for mapping back during reconciliation
            provenance_map[match.start()] = {
                "provenance_state": "HUMAN_EDITED",
                "originator": "AI_Assistant",
                "editor": author,
                "timestamp": timestamp,
                "has_human_edits": True
            }

        for match in del_matches:
            attrs = match.group(1).decode('utf-8', errors='ignore')
            author_match = re.search(r'w:author="([^"]+)"', attrs)
            date_match = re.search(r'w:date="([^"]+)"', attrs)
            
            author = author_match.group(1) if author_match else "Unknown_Editor"
            timestamp = date_match.group(1) if date_match else None
            
            provenance_map[match.start()] = {
                "provenance_state": "HUMAN_EDITED",
                "originator": "AI_Assistant",
                "editor": author,
                "timestamp": timestamp,
                "has_human_edits": True
            }

        return provenance_map


class StructuralCompiler:
    """MIMD Master Compiler: Orchestrates Stream A, Stream B, and SIMD Stream C parallel execution threads and reconciles outputs."""

    def __init__(self, doc_file: Any, doc_name: str) -> None:
        self.doc_name: str = doc_name
        self.archive: zipfile.ZipFile = zipfile.ZipFile(doc_file)
        self.styles: Dict[str, str] = self._load_styles()
        self.resolution_matrix: ResolutionMatrix = ResolutionMatrix()
        self.current_category: Optional[str] = None

    def _load_styles(self) -> Dict[str, str]:
        styles: Dict[str, str] = {}
        try:
            with self.archive.open("word/styles.xml") as f:
                root: ET._Element = ET.parse(f).getroot()
                for style in root.findall(".//w:style", NS_MAP):
                    s_id = style.get(f"{{{NS_W}}}val") or style.get(f"{{{NS_W}}}styleId")
                    name_elem = style.find(".//w:name", NS_MAP)
                    if s_id:
                        styles[s_id] = name_elem.get(f"{{{NS_W}}}val") if name_elem is not None else s_id
        except (KeyError, ET.ParseError):
            pass
        return styles

    def _generate_node_id(self, dewey_id: str) -> str:
        return f"urn:trace:doc:{self.doc_name}:node:dewey:{dewey_id}"

    def build_full_dag(self) -> List[ChestnutNode]:
        """Runs Stream A, Stream B, and SIMD Stream C in parallel threads, then passes outputs to Reconciliation Engine."""
        roots: List[ChestnutNode] = []
        part_names = [f for f in self.archive.namelist() if f.startswith("word/") and f.endswith(".xml")]
        
        if "word/document.xml" in part_names:
            part_names.remove("word/document.xml")
            part_names.insert(0, "word/document.xml")

        for idx, part_name in enumerate(part_names, start=1):
            try:
                with self.archive.open(part_name) as f:
                    xml_bytes = f.read()
                    root_elem: ET._Element = ET.fromstring(xml_bytes)
                    prefix = str(idx)

                    # --- MIMD Tri-Stream Parallel Execution ---
                    worker_a = ContentWorkerStreamA()
                    worker_b = TopologyWorkerStreamB()
                    worker_c = ProvenanceWorkerStreamC()

                    with ThreadPoolExecutor(max_workers=3) as executor:
                        future_a = executor.submit(worker_a.process, root_elem)
                        future_b = executor.submit(worker_b.process, root_elem, self.styles)
                        future_c = executor.submit(worker_c.process_vectorized_bytes, xml_bytes)

                        content_map = future_a.result()
                        topology_map = future_b.result()
                        provenance_map = future_c.result()

                    # --- Stream Reconciliation Node ---
                    dag_root = self._reconcile_streams(prefix, content_map, topology_map, provenance_map)
                    roots.append(dag_root)

            except Exception:
                continue

        return roots

    def _reconcile_streams(
        self, prefix: str, content_map: Dict[str, Dict[str, str]], topology_map: Dict[str, Dict[str, Any]], provenance_map: Dict[int, Dict[str, Any]]
    ) -> ChestnutNode:
        """Joins Stream A (Text/Tabs), Stream B (Dewey Topology), and Stream C (Provenance Ledger) into unified Chestnut DAG Nodes."""
        
        nodes_dict: Dict[str, ChestnutNode] = {}
        anchor_dewey = prefix

        # Extract aggregate provenance defaults if any human edits were found in stream C
        prov_state = "AI_GENERATED"
        editor = None
        timestamp = None
        has_edits = False
        if provenance_map:
            # Take the first matched revision signature or synthesize aggregate state
            first_prov = next(iter(provenance_map.values()))
            prov_state = first_prov["provenance_state"]
            editor = first_prov["editor"]
            timestamp = first_prov["timestamp"]
            has_edits = first_prov["has_human_edits"]

        for raw_key, topo in topology_map.items():
            dewey_id = f"{prefix}.{raw_key}" if raw_key != "1" else prefix
            node_id = self._generate_node_id(dewey_id)

            content = content_map.get(raw_key, {"raw_text": "", "clean_text": ""})
            raw_text = content["raw_text"]
            clean_text = content["clean_text"]

            resolved_style = topo["style_id"]

            if any(h in resolved_style.lower() for h in ["heading", "title"]) and clean_text:
                self.current_category = clean_text
                anchor_dewey = dewey_id

            if any(h in resolved_style.lower() for h in ["heading", "title"]):
                delta_dewey = dewey_id
            else:
                delta_offset = dewey_id.replace(f"{anchor_dewey}.", "+")
                delta_dewey = delta_offset if delta_offset.startswith("+") else f"+{dewey_id}"

            style_vector = StyleDisplacementVector()
            if "heading 1" in resolved_style.lower():
                style_vector.size_offset_pt = 9.0
                style_vector.weight_delta = 1
            elif "heading 2" in resolved_style.lower():
                style_vector.size_offset_pt = 5.0
                style_vector.weight_delta = 1

            node = ChestnutNode(
                node_id=node_id,
                dewey_id=dewey_id,
                delta_dewey=delta_dewey,
                tag=topo["tag"],
                path=topo["path"],
                normalized_path=topo["normalized_path"],
                text=raw_text,
                clean_text=clean_text,
                style_id=resolved_style,
                depth=topo["depth"],
                in_table=topo["in_table"],
                in_textbox=topo["in_textbox"],
                row_index=topo["row_index"],
                column_index=topo["column_index"],
                is_header_cell=topo["is_header"],
                grid_span=topo["grid_span"],
                has_virtual_tab=topo["has_virtual_tab"],
                inferred_category=self.current_category,
                extracted_dates=TopologyWorkerStreamB.DATE_PATTERN.findall(clean_text),
                provenance_state=prov_state,
                originator="AI_Assistant",
                editor=editor,
                approver=editor if has_edits else None,
                revision_timestamp=timestamp,
                has_human_edits=has_edits,
                style_vector=style_vector,
            )

            nodes_dict[raw_key] = node

        for raw_key, node in nodes_dict.items():
            if raw_key != "1":
                parent_key = ".".join(raw_key.split(".")[:-1])
                if parent_key in nodes_dict:
                    parent_node = nodes_dict[parent_key]
                    node.parent_id = parent_node.node_id
                    parent_node.children.append(node)

        return nodes_dict["1"]

    def bifurcate(
        self, node: ChestnutNode, ledger: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        if (node.tag == "t" or node.tag == "tab") and (node.text or node.has_virtual_tab):
            state, confidence, query_evidence = self.resolution_matrix.collapse(node)

            record: Dict[str, Any] = {
                "NodeID": node.node_id,
                "DeweyID": node.dewey_id,
                "DeltaDewey": node.delta_dewey,
                "DeweyDepth": node.depth,
                "ParentID": node.parent_id,
                "State": state,
                "Confidence": round(confidence, 4),
                "Style": node.style_id,
                "StyleDeltaMagnitude": round(node.style_vector.magnitude(), 2),
                "Path": node.normalized_path,
                "Content": node.text,
                "CleanContent": node.clean_text,
                "RowIndex": node.row_index,
                "ColumnIndex": node.column_index,
                "IsHeaderCell": node.is_header_cell,
                "GridSpan": node.grid_span,
                "HasVirtualTab": node.has_virtual_tab,
                "InferredCategory": node.inferred_category,
                "ExtractedDates": node.extracted_dates,
                "TopologicalParity": -1 if node.in_table or node.in_textbox else 1,
                "ValidationQuery": query_evidence,
                "ProvenanceState": node.provenance_state,
                "Originator": node.originator,
                "Editor": node.editor,
                "Approver": node.approver,
                "RevisionTimestamp": node.revision_timestamp,
                "HasHumanEdits": node.has_human_edits,
                "RemediationHistory": [],
            }

            if state != "Quarantined":
                ledger["Validated"].append(record)
            else:
                ledger["Quarantined"].append(record)

        for child in node.children:
            self.bifurcate(child, ledger)


# --- Node Coalescing & Boundary Repair Transformation ---


def coalesce_atoms(
    atoms: List[Dict[str, Any]], strict_parent_matching: bool = True
) -> List[Dict[str, Any]]:
    if not atoms:
        return []

    coalesced: List[Dict[str, Any]] = []
    current_node = dict(atoms[0])

    for next_node in atoms[1:]:
        same_path = current_node.get("Path") == next_node.get("Path")
        same_style = current_node.get("Style") == next_node.get("Style")

        if strict_parent_matching:
            same_scope = current_node.get("ParentID") == next_node.get("ParentID")
        else:
            same_scope = same_path and same_style

        if same_path and same_style and same_scope:
            text1 = current_node.get("Content", "")
            text2 = next_node.get("Content", "")

            clean1 = current_node.get("CleanContent", "")
            clean2 = next_node.get("CleanContent", "")

            start_dewey = current_node["DeweyID"].split("-")[0]
            end_dewey = next_node["DeweyID"].split("-")[-1]
            current_node["DeweyID"] = f"{start_dewey}-{end_dewey}"

            if text2 in [".", ",", ";", ":", "s", "s.", " ", ")", "]"] or text1.endswith("-"):
                current_node["Content"] = f"{text1}{text2}"
            elif text2 == "\t" or text1 == "\t":
                current_node["Content"] = f"{text1}{text2}"
            else:
                current_node["Content"] = f"{text1} {text2}".strip()

            if clean2 in [".", ",", ";", ":", "s", "s.", " ", ")", "]"] or clean1.endswith("-"):
                current_node["CleanContent"] = f"{clean1}{clean2}"
            elif clean2 == "\t" or clean1 == "\t":
                current_node["CleanContent"] = f"{clean1}{clean2}"
            else:
                current_node["CleanContent"] = f"{clean1} {clean2}".strip()

            current_node["ExtractedDates"] = list(
                set(current_node.get("ExtractedDates", []) + next_node.get("ExtractedDates", []))
            )
        else:
            coalesced.append(current_node)
            current_node = dict(next_node)

    coalesced.append(current_node)
    return coalesced


# --- Template Compare & Pre-Flight Engine ---


class TemplateCompareEngine:
    def __init__(self, ref_ledger: Dict[str, List[Dict[str, Any]]], var_ledger: Dict[str, List[Dict[str, Any]]]) -> None:
        self.ref_atoms = ref_ledger["Validated"]
        self.var_atoms = var_ledger["Validated"]
        self.var_quarantine = var_ledger["Quarantined"]

    def execute_preflight_check(self) -> Dict[str, Any]:
        ref_headings = {a["Content"].strip().lower() for a in self.ref_atoms if a["State"] == "Native_Heading"}
        var_headings = {a["Content"].strip().lower() for a in self.var_atoms if a["State"] == "Native_Heading"}

        missing_sections = list(ref_headings - var_headings)
        added_sections = list(var_headings - ref_headings)

        raw_text = " ".join([a["Content"] for a in self.var_atoms + self.var_quarantine])
        raw_token_count = max(1, len(raw_text) // 4)

        json_ld_str = json.dumps(export_to_json_ld_dict("variant", coalesce_atoms(self.var_atoms)))
        optimized_token_count = max(1, len(json_ld_str) // 4)

        token_savings_pct = max(0.0, float((raw_token_count - optimized_token_count) / raw_token_count * 100))

        confidence_scores = [a["Confidence"] for a in self.var_atoms]
        avg_confidence = float(np.mean(confidence_scores)) if confidence_scores else 0.0

        status = "PASSED" if not missing_sections and len(self.var_quarantine) == 0 else "WARNING"

        return {
            "status": status,
            "governance_confidence": round(avg_confidence, 4),
            "missing_template_sections": missing_sections,
            "added_variant_sections": added_sections,
            "raw_token_estimate": raw_token_count,
            "graph_token_estimate": optimized_token_count,
            "token_reduction_pct": round(token_savings_pct, 1),
            "quarantined_count": len(self.var_quarantine),
            "validated_node_count": len(self.var_atoms),
        }


# --- Fully Enriched JSON-LD Exporter ---


def export_to_json_ld_dict(
    file_name: str, validated_atoms: List[Dict[str, Any]]
) -> Dict[str, Any]:
    graph_nodes: List[Dict[str, Any]] = []

    for atom in validated_atoms:
        schema_type: str = (
            "DigitalDocumentSection"
            if atom["State"] == "Native_Heading"
            else "TextDigitalDocument"
        )

        ld_node: Dict[str, Any] = {
            "@id": atom["NodeID"],
            "@type": [schema_type, "trace:ChestnutAtom"],
            "schema:name": atom["Style"],
            "schema:text": atom["Content"],
            "trace:cleanText": atom.get("CleanContent", atom["Content"]),
            "trace:deweyCoordinate": atom["DeweyID"],
            "trace:deltaDeweyCoordinate": atom.get("DeltaDewey", atom["DeweyID"]),
            "trace:deweyDepth": atom["DeweyDepth"],
            "trace:styleDisplacementMagnitude": atom.get("StyleDeltaMagnitude", 0.0),
            "trace:normalizedPath": atom["Path"],
            "trace:collapseConfidence": atom["Confidence"],
            "trace:semanticState": atom["State"],
            "trace:topologicalParity": atom["TopologicalParity"],
            "trace:provenanceState": atom.get("ProvenanceState", "AI_GENERATED"),
            "trace:originator": atom.get("Originator", "AI_Assistant"),
            "trace:editor": atom.get("Editor"),
            "trace:approver": atom.get("Approver"),
            "prov:wasGeneratedBy": atom.get("ValidationQuery"),
        }

        if atom.get("RowIndex") is not None:
            ld_node["trace:rowIndex"] = atom["RowIndex"]
        if atom.get("ColumnIndex") is not None:
            ld_node["trace:columnIndex"] = atom["ColumnIndex"]
        if atom.get("GridSpan", 1) > 1:
            ld_node["trace:gridSpan"] = atom["GridSpan"]
        if atom.get("IsHeaderCell"):
            ld_node["trace:isHeaderCell"] = True
        if atom.get("HasVirtualTab"):
            ld_node["trace:hasVirtualTab"] = True

        if atom.get("InferredCategory"):
            ld_node["trace:inferredCategory"] = atom["InferredCategory"]
        if atom.get("ExtractedDates"):
            ld_node["trace:extractedDates"] = atom["ExtractedDates"]

        if atom.get("RemediationHistory"):
            ld_node["trace:remediationHistory"] = atom["RemediationHistory"]

        if atom.get("ParentID"):
            ld_node["trace:hasParent"] = {"@id": atom["ParentID"]}

        graph_nodes.append(ld_node)

    return {
        "@context": {
            "schema": "https://schema.org/",
            "trace": "https://trace.chestnut.org/schema/v2/",
            "prov": "http://www.w3.org/ns/prov#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        "@id": f"urn:trace:doc:{file_name}",
        "@type": ["schema:DigitalDocument", "prov:Entity"],
        "schema:name": file_name,
        "trace:governanceStatus": "Validated",
        "@graph": graph_nodes,
    }


def get_semantic_rank(style_name: str) -> str:
    s: str = style_name.lower()
    if "heading" in s or "title" in s:
        return "Heading"
    if "table" in s or "grid" in s:
        return "Table_Atom"
    if "normal" in s or "body" in s:
        return "Body_Text"
    return "Other"


def to_markdown(validated_ledger_data: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    
    for item in validated_ledger_data:
        if item.get("State") == "Quarantined":
            continue

        style: str = item["Style"].lower()
        content: str = item.get("CleanContent", item.get("Content", "")).strip()

        if not content or content in [".", ",", ";", ":", "-"]:
            continue

        content = content.replace("\t", " | ")

        if "heading 1" in style:
            lines.append(f"# {content}\n")
        elif "heading 2" in style:
            lines.append(f"## {content}\n")
        elif "heading 3" in style:
            lines.append(f"### {content}\n")
        else:
            lines.append(f"{content}\n")

    return "\n".join(lines)


# --- Visual Integration Components ---

def render_query_distribution(df: pd.DataFrame) -> None:
    """Renders a donut chart showing the volume of data atoms resolved by each specific query."""
    st.subheader("Macro Resolution Distribution")
    
    if "ValidationQuery" not in df.columns:
        return

    distribution_chart = alt.Chart(df).mark_arc(innerRadius=60, stroke="#fff").encode(
        theta=alt.Theta(field="count", type="quantitative"),
        color=alt.Color(
            field="ValidationQuery", 
            type="nominal", 
            legend=alt.Legend(title="Trigger Query", orient="right", labelLimit=300)
        ),
        tooltip=[
            alt.Tooltip('ValidationQuery:N', title='Query Logic'),
            alt.Tooltip('count:Q', title='Nodes Captured')
        ]
    ).transform_aggregate(
        count='count()',
        groupby=['ValidationQuery']
    ).properties(
        width=350,
        height=320,
        title="Node Volume per Resolution Rule"
    ).configure(
        padding={"left": 30, "right": 20, "top": 20, "bottom": 20}
    )
    
    col_chart, col_spacer = st.columns([2, 1])
    with col_chart:
        st.altair_chart(distribution_chart, use_container_width=True)


def render_audit_trail(df: pd.DataFrame, cols_to_show: List[str]) -> None:
    st.subheader("Validated Provenance Ledger")
    
    if "ValidationQuery" not in df.columns:
        st.info("No query provenance data found in this graph.")
        return

    queries_executed = df['ValidationQuery'].dropna().unique()
    
    if len(queries_executed) == 0:
        st.info("No query provenance data found in this graph.")
        return

    for query in queries_executed:
        rule_df = df[df['ValidationQuery'] == query]
        node_count = len(rule_df)
        
        with st.expander(f"⚙️ Rule Executed: {query} ({node_count} nodes)"):
            st.dataframe(
                rule_df[cols_to_show],
                use_container_width=True,
                hide_index=True
            )


def render_revision_diff_audit(df: pd.DataFrame) -> None:
    """Renders Stream C Tracked Changes & Provenance Diff Audit Tab."""
    st.subheader("Revision & Diff Audit Trail (Stream C)")
    
    if "ProvenanceState" not in df.columns:
        st.info("No provenance state metadata captured.")
        return

    edited_df = df[df["HasHumanEdits"] == True]
    ai_df = df[df["HasHumanEdits"] == False]

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Atoms", len(df))
    m2.metric("AI-Generated Baseline Atoms", len(ai_df))
    m3.metric("Human-Edited / Reviewed Atoms", len(edited_df))

    st.divider()

    if len(edited_df) > 0:
        st.caption("Inspecting granular human revisions, author metadata, and diff markup extracted via Stream C SIMD scanning:")
        st.dataframe(
            edited_df[["DeweyID", "Style", "Editor", "RevisionTimestamp", "ProvenanceState", "CleanContent"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("Document matches baseline AI generation. Zero human-in-the-loop override markers detected.")


# --- Streamlit Engine Application ---


def main() -> None:
    st.set_page_config(layout="wide", page_title="Chestnut TRACE Engine v5.0.2 (SIMD Multi-Stream Edition)")

    st.sidebar.title("TRACE Control Surface")

    persona_mode = st.sidebar.selectbox(
        "User Profile / Preset View",
        [
            "Knowledge Worker (Reader Mode)",
            "System Auditor (Lossless Mode)",
            "Developer (Graph & Vector Mode)",
        ],
    )

    st.sidebar.divider()
    st.sidebar.subheader("Granular View Toggles")

    default_coalesce = persona_mode == "Knowledge Worker (Reader Mode)"
    default_show_vector = persona_mode == "Developer (Graph & Vector Mode)"
    default_show_ids = persona_mode != "Knowledge Worker (Reader Mode)"
    default_strict_parent = persona_mode == "System Auditor (Lossless Mode)"

    enable_coalesce = st.sidebar.toggle(
        "Enable Node Coalescing & Boundary Repair", value=default_coalesce
    )
    strict_parent_matching = st.sidebar.toggle(
        "Strict Parent Container Matching", value=default_strict_parent
    )
    show_vector_details = st.sidebar.toggle(
        "Show Vector Coordinates & Parity", value=default_show_vector
    )
    show_node_ids = st.sidebar.toggle(
        "Show Node IDs & Parent Links", value=default_show_ids
    )

    st.title("Chestnut TRACE: Comparative Governance Engine (v5.0.2 - SIMD Multi-Stream Edition)")

    mode: str = st.radio(
        "Audit Mode", ["Single SOP Audit", "Template vs. Variant"], horizontal=True
    )

    if "processed_data" not in st.session_state:
        st.session_state.processed_data = {}

    if mode == "Single SOP Audit":
        uploaded_files = st.file_uploader(
            "Upload SOPs",
            type=["docx"],
            accept_multiple_files=True,
            key="single_upload",
        )
        if uploaded_files:
            for file in uploaded_files:
                if file.name not in st.session_state.processed_data:
                    compiler = StructuralCompiler(file, file.name)
                    dag_roots = compiler.build_full_dag()
                    ledger: Dict[str, List[Dict[str, Any]]] = {
                        "Validated": [],
                        "Quarantined": [],
                        "Pruned": [],
                    }
                    for root in dag_roots:
                        compiler.bifurcate(root, ledger)
                    st.session_state.processed_data[file.name] = ledger

    elif mode == "Template vs. Variant":
        col1, col2 = st.columns(2)
        ref_file = col1.file_uploader(
            "Master Template", type=["docx"], key="ref_upload"
        )
        var_files = col2.file_uploader(
            "Variants", type=["docx"], accept_multiple_files=True, key="var_upload"
        )

        if ref_file and var_files:
            for file in [ref_file] + var_files:
                if file.name not in st.session_state.processed_data:
                    compiler = StructuralCompiler(file, file.name)
                    dag_roots = compiler.build_full_dag()
                    ledger: Dict[str, List[Dict[str, Any]]] = {
                        "Validated": [],
                        "Quarantined": [],
                        "Pruned": [],
                    }
                    for root in dag_roots:
                        compiler.bifurcate(root, ledger)
                    st.session_state.processed_data[file.name] = ledger

            st.divider()
            st.subheader("⚙️ Phase 1: Structural & Semantic Pre-Flight Audit")

            ref_ledger = st.session_state.processed_data[ref_file.name]
            var_file_selected = st.selectbox("Select Variant to Compare against Master:", [v.name for v in var_files])
            var_ledger = st.session_state.processed_data[var_file_selected]

            compare_engine = TemplateCompareEngine(ref_ledger, var_ledger)
            manifest = compare_engine.execute_preflight_check()

            status_color = "green" if manifest["status"] == "PASSED" else "orange"
            st.markdown(f":{status_color}[**Pre-Flight Status:** {manifest['status']}] • **Governance Confidence:** `{manifest['governance_confidence']}`")

            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Raw Token Est.", f"{manifest['raw_token_estimate']:,}")
            p2.metric("Graph Token Est.", f"{manifest['graph_token_estimate']:,}")
            p3.metric("Context Reduction", f"{manifest['token_reduction_pct']}%")
            p4.metric("Quarantined Items", manifest['quarantined_count'])

            if manifest["missing_template_sections"]:
                st.warning(f"⚠️ Structural Drift Detected: Missing Template Sections: {', '.join(manifest['missing_template_sections'])}")
            if manifest["added_variant_sections"]:
                st.info(f"ℹ️ Variant Expansion: Additional Sections Detected: {', '.join(manifest['added_variant_sections'])}")

    if st.session_state.processed_data:
        st.divider()
        selected_file: str = st.selectbox(
            "Select Document Ledger to Audit",
            list(st.session_state.processed_data.keys()),
        )

        file_ledger = st.session_state.processed_data[selected_file]
        raw_validated = file_ledger["Validated"]
        quarantined_data = file_ledger["Quarantined"]
        pruned_data = file_ledger.get("Pruned", [])

        display_validated = (
            coalesce_atoms(
                raw_validated, strict_parent_matching=strict_parent_matching
            )
            if enable_coalesce
            else raw_validated
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Display Atoms", len(display_validated))
        m2.metric("Raw Structural Atoms", len(raw_validated))
        m3.metric("Quarantined Anomalies", len(quarantined_data))
        total_atoms: int = len(raw_validated) + len(quarantined_data) + len(pruned_data)
        governance_rate: float = (
            (len(raw_validated) / total_atoms * 100) if total_atoms > 0 else 0.0
        )
        m4.metric("Governance Score", f"{governance_rate:.1f}%")

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
            [
                "Pulse Graph",
                "Markdown Preview",
                "Validated Ledger",
                "Revision & Diff Audit",
                "Quarantine & Aux Audit",
                "Graph / JSON-LD Export",
            ]
        )

        with tab1:
            if display_validated:
                df = pd.DataFrame(display_validated)
                df["Category"] = df["Style"].apply(get_semantic_rank)

                render_query_distribution(df)
                
                st.divider()
                
                st.subheader("Topological Sequence Pulse Graph (Linear View)")
                chart = (
                    alt.Chart(df)
                    .mark_point(filled=True, opacity=0.8, size=95)
                    .encode(
                        x=alt.X(
                            "DeweyID:N",
                            sort=None,
                            title="Dewey Coordinate Topology Sequence",
                        ),
                        y=alt.Y(
                            "Category:N",
                            sort=[
                                "Heading",
                                "Body_Text",
                                "Table_Atom",
                                "Other",
                            ],
                            title="Semantic Category",
                        ),
                        color=alt.Color("Category:N", legend=alt.Legend(title="Category")),
                        shape=alt.Shape(
                            "ValidationQuery:N",
                            title="Resolution Rule",
                            scale=alt.Scale(range=['circle', 'square', 'triangle-up', 'cross', 'diamond', 'triangle-down'])
                        ),
                        tooltip=[
                            "NodeID",
                            "DeweyID",
                            "DeltaDewey",
                            "DeweyDepth",
                            "Style",
                            "RowIndex",
                            "ColumnIndex",
                            "InferredCategory",
                            "ExtractedDates",
                            "CleanContent",
                            "ValidationQuery",
                            "Confidence"
                        ],
                    )
                    .properties(height=420)
                    .interactive()
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("No validated atoms available for Pulse Graph visualization.")

        with tab2:
            st.markdown(to_markdown(display_validated))

        with tab3:
            df_ledger = pd.DataFrame(display_validated)
            cols_to_show = [
                "CleanContent",
                "Style",
                "RowIndex",
                "ColumnIndex",
                "InferredCategory",
                "ExtractedDates",
            ]

            if show_node_ids:
                cols_to_show = ["DeweyID", "DeltaDewey", "NodeID", "ParentID"] + cols_to_show
            if show_vector_details:
                cols_to_show += ["DeweyDepth", "StyleDeltaMagnitude", "Path", "TopologicalParity", "Confidence", "State"]

            render_audit_trail(df_ledger, cols_to_show)

        with tab4:
            df_ledger = pd.DataFrame(display_validated)
            render_revision_diff_audit(df_ledger)

        with tab5:
            st.subheader("Auxiliary Container Audit")
            aux_atoms = [a for a in display_validated if a["State"] == "Auxiliary_Container"]
            st.metric("Total Auxiliary Items Captured", len(aux_atoms))

            if aux_atoms:
                df_aux = pd.DataFrame(aux_atoms)
                st.caption("Reviewing captured non-body, floating, frame, or callout elements:")
                st.dataframe(
                    df_aux[["DeweyID", "Style", "Path", "CleanContent", "TopologicalParity"]],
                    use_container_width=True,
                )
            else:
                st.info("No auxiliary container elements detected in this document.")

            st.divider()

            st.subheader("Vector Quarantine Isolation & Scoped Remediation")
            if quarantined_data:
                st.error(
                    f"Quarantine Containment: {len(quarantined_data)} semantic or visual anomalies isolated."
                )

                quarantine_prefixes = sorted(list(set([a["DeweyID"].split(".")[0] for a in quarantined_data])))
                
                selected_prefix = st.selectbox(
                    "Select Section Subtree / Dewey Coordinate Root to Remediate:",
                    quarantine_prefixes,
                    format_func=lambda p: f"Section Subtree (Dewey Root: {p}.x)"
                )

                scoped_items = [a for a in quarantined_data if a["DeweyID"].startswith(f"{selected_prefix}.")]

                st.caption(f"Displaying {len(scoped_items)} quarantined atoms within Subtree Root `{selected_prefix}`:")
                df_scoped = pd.DataFrame(scoped_items)
                st.dataframe(
                    df_scoped[["DeweyID", "Style", "StyleDeltaMagnitude", "CleanContent", "State", "ValidationQuery"]],
                    use_container_width=True,
                )

                col_approve, col_reject, _ = st.columns([1, 1, 2])

                with col_approve:
                    if st.button("Approve & Restore Subtree", type="primary"):
                        for item in scoped_items:
                            quarantined_data.remove(item)
                            item["State"] = "Repaired_Validated"
                            item["RemediationHistory"].append({"action": "Approved", "timestamp": "2026-08-18"})
                            raw_validated.append(item)
                        st.success(f"Subtree {selected_prefix} approved and restored to active graph.")
                        st.rerun()

                with col_reject:
                    if st.button("Reject & Suppress Subtree"):
                        for item in scoped_items:
                            quarantined_data.remove(item)
                            item["State"] = "Pruned"
                            item["RemediationHistory"].append({"action": "Rejected", "timestamp": "2026-08-18"})
                            pruned_data.append(item)
                        st.warning(f"Subtree {selected_prefix} pruned and suppressed with deterministic fallback.")
                        st.rerun()

            else:
                st.success("Zero anomalies detected in quarantine. Baseline compliant.")

        with tab6:
            json_ld_dict = export_to_json_ld_dict(selected_file, display_validated)
            json_ld_str = json.dumps(json_ld_dict, indent=2)

            st.subheader("Interoperable Knowledge Graph (JSON-LD)")
            st.caption(
                "Export structured RDF graph containing absolute and delta Dewey coordinates, explicit tabular row/col indices, repaired text streams, category tags, and provenance metadata."
            )

            st.download_button(
                label="Download JSON-LD Graph Document",
                data=json_ld_str,
                file_name=f"{selected_file}_trace_graph.jsonld",
                mime="application/ld+json",
            )

            st.json(json_ld_dict)


if __name__ == "__main__":
    main()
