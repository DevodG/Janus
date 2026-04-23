"""
Scam Journey Graph Engine — Relational memory for ZeroTrust Guardian.
Part of the Janus Scam Journey Guardian Milestone 2.
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional
import hashlib
import networkx as nx

logger = logging.getLogger(__name__)

class ScamGraphEngine:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
        self.db_path = os.path.join(self.cache_dir, "scam_journeys.json")
        
        # Ensure cache dir exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Load existing graph
        self._load_graph()

    def _hash_id(self, value: str) -> str:
        """Privacy-preserving hashing for identifiers (Phone, UPI, etc)."""
        return hashlib.sha256(value.strip().lower().encode()).hexdigest()[:16]

    def add_event(self, channel: str, entities: Dict[str, List[str]], risk_signals: Dict[str, int]):
        """
        Add a threat event to the graph and link entities.
        Entities structure: {"phones": [], "upi_ids": [], "links": []}
        """
        timestamp = time.time()
        event_id = f"evt_{int(timestamp)}_{channel}"
        
        # Add the event node
        self.graph.add_node(event_id, type="event", channel=channel, signals=risk_signals, ts=timestamp)
        
        # Add and link entity nodes
        for category, items in entities.items():
            for item in items:
                h_id = self._hash_id(item)
                # Link category to hashed identity
                entity_node = f"ent_{category}_{h_id}"
                
                if not self.graph.has_node(entity_node):
                    self.graph.add_node(entity_node, type="entity", category=category, raw_hint=item[:4] + "***")
                
                # Direct edge: Event -> Entity (Observed in this event)
                self.graph.add_edge(event_id, entity_node, relationship="contains")
                
                # Check for existing journeys (co-occurrence)
                # This automatically builds the "Story" by connecting nodes that share entities.
        
        self._save_graph()
        logger.info(f"[SCAM-GRAPH] Added event {event_id} and linked {sum(len(v) for v in entities.values())} entities.")

    def get_journey_score(self, entities: Dict[str, List[str]]) -> Dict[str, Any]:
        """Calculate the highest risk score among all provided entities."""
        max_score = 0.0
        best_report = {"score": 0.0, "event_count": 0, "status": "CLEAN"}
        
        for category, items in entities.items():
            for item in items:
                h_id = self._hash_id(item)
                node_id = f"ent_{category}_{h_id}"
                
                if not self.graph.has_node(node_id):
                    continue
                
                # Find all reachable events from this entity
                undirected = self.graph.to_undirected()
                try:
                    connected_component = nx.node_connected_component(undirected, node_id)
                    subgraph = self.graph.subgraph(connected_component)
                    
                    event_nodes = [n for n, d in subgraph.nodes(data=True) if d.get("type") == "event"]
                    entity_nodes = [n for n, d in subgraph.nodes(data=True) if d.get("type") == "entity"]
                    channels = set(subgraph.nodes[n].get("channel") for n in event_nodes)
                    
                    score = len(event_nodes) * 20
                    if len(channels) > 1:
                        score *= 1.5
                    
                    if score > max_score:
                        max_score = score
                        best_report = {
                            "score": min(score, 100.0),
                            "event_count": len(event_nodes),
                            "entity_count": len(entity_nodes),
                            "channels": list(channels),
                            "status": "SUSPICIOUS" if score > 40 else "BLOCKED" if score > 80 else "CLEAN"
                        }
                except Exception as e:
                    logger.error(f"[SCAM-GRAPH] Single Entity Score Compute Fail: {e}")
        
        return best_report

    def _save_graph(self):
        """Persist graph nodes and edges to JSON."""
        data = {
            "nodes": list(self.graph.nodes(data=True)),
            "edges": list(self.graph.edges(data=True))
        }
        with open(self.db_path, "w") as f:
            json.dump(data, f)

    def _load_graph(self):
        """Restore graph from JSON."""
        if not os.path.exists(self.db_path):
            return
        try:
            with open(self.db_path, "r") as f:
                data = json.load(f)
                self.graph.add_nodes_from(data["nodes"])
                self.graph.add_edges_from(data["edges"])
            logger.info(f"[SCAM-GRAPH] Restored graph with {len(self.graph.nodes)} nodes.")
        except Exception as e:
            logger.error(f"[SCAM-GRAPH] Load Fail: {e}")

scam_graph = ScamGraphEngine()
