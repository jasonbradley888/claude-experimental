"""Graph algorithms using NetworkX."""

from typing import List, Optional, Set, Tuple

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

from ..core.models import Entity, Relation


def _check_networkx():
    """Raise error if NetworkX is not installed."""
    if not HAS_NETWORKX:
        raise ImportError(
            "NetworkX is required for graph algorithms. "
            "Install with: pip install networkx"
        )


def build_networkx_graph(
    entities: List[Entity],
    relations: List[Relation],
    directed: bool = True
) -> "nx.DiGraph | nx.Graph":
    """Build a NetworkX graph from entities and relations.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        directed: If True, create DiGraph; if False, create Graph

    Returns:
        NetworkX DiGraph or Graph
    """
    _check_networkx()

    G = nx.DiGraph() if directed else nx.Graph()

    # Add nodes with attributes
    for entity in entities:
        G.add_node(
            entity.name,
            type=entity.type,
            observations=entity.observations,
            created_at=entity.created_at
        )

    # Add edges with attributes
    for rel in relations:
        G.add_edge(
            rel.from_entity,
            rel.to_entity,
            relation_type=rel.relation_type,
            created_at=rel.created_at
        )

    return G


def shortest_path(
    entities: List[Entity],
    relations: List[Relation],
    source: str,
    target: str
) -> Optional[List[str]]:
    """Find shortest path between two entities.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        source: Source entity name
        target: Target entity name

    Returns:
        List of entity names in the path, or None if no path exists
    """
    _check_networkx()

    # Build undirected graph for path finding
    G = build_networkx_graph(entities, relations, directed=False)

    if source not in G or target not in G:
        return None

    try:
        return nx.shortest_path(G, source, target)
    except nx.NetworkXNoPath:
        return None


def all_paths(
    entities: List[Entity],
    relations: List[Relation],
    source: str,
    target: str,
    max_depth: int = 10
) -> List[List[str]]:
    """Find all paths between two entities up to max depth.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        source: Source entity name
        target: Target entity name
        max_depth: Maximum path length

    Returns:
        List of paths (each path is a list of entity names)
    """
    _check_networkx()

    G = build_networkx_graph(entities, relations, directed=False)

    if source not in G or target not in G:
        return []

    try:
        paths = list(nx.all_simple_paths(G, source, target, cutoff=max_depth))
        return paths
    except nx.NetworkXNoPath:
        return []


def connected_components(
    entities: List[Entity],
    relations: List[Relation]
) -> List[Set[str]]:
    """Find connected components in the graph.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects

    Returns:
        List of sets, each containing entity names in a connected component
    """
    _check_networkx()

    G = build_networkx_graph(entities, relations, directed=False)
    return [set(comp) for comp in nx.connected_components(G)]


def extract_subgraph(
    entities: List[Entity],
    relations: List[Relation],
    root: str,
    depth: int = 3
) -> Tuple[List[str], List[Relation]]:
    """Extract subgraph centered on root entity using BFS.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        root: Root entity name to start from
        depth: Maximum depth to traverse

    Returns:
        Tuple of (entity names in subgraph, relations in subgraph)
    """
    _check_networkx()

    G = build_networkx_graph(entities, relations, directed=True)

    if root not in G:
        return [], []

    # Use BFS to find nodes within depth
    # For directed graph, we want to follow edges in both directions
    visited = {root}
    current_level = {root}

    for _ in range(depth):
        next_level = set()
        for node in current_level:
            # Follow outgoing edges
            for successor in G.successors(node):
                if successor not in visited:
                    next_level.add(successor)
                    visited.add(successor)
            # Follow incoming edges
            for predecessor in G.predecessors(node):
                if predecessor not in visited:
                    next_level.add(predecessor)
                    visited.add(predecessor)

        if not next_level:
            break
        current_level = next_level

    # Get relations within subgraph
    subgraph_relations = [
        rel for rel in relations
        if rel.from_entity in visited and rel.to_entity in visited
    ]

    return list(visited), subgraph_relations


def get_descendants(
    entities: List[Entity],
    relations: List[Relation],
    root: str
) -> Set[str]:
    """Get all descendants (reachable via outgoing edges) from root.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        root: Root entity name

    Returns:
        Set of entity names reachable from root
    """
    _check_networkx()

    G = build_networkx_graph(entities, relations, directed=True)

    if root not in G:
        return set()

    return set(nx.descendants(G, root))


def get_ancestors(
    entities: List[Entity],
    relations: List[Relation],
    target: str
) -> Set[str]:
    """Get all ancestors (can reach target via outgoing edges) of target.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects
        target: Target entity name

    Returns:
        Set of entity names that can reach target
    """
    _check_networkx()

    G = build_networkx_graph(entities, relations, directed=True)

    if target not in G:
        return set()

    return set(nx.ancestors(G, target))


def topological_sort(
    entities: List[Entity],
    relations: List[Relation]
) -> Optional[List[str]]:
    """Return topological ordering of entities if graph is a DAG.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects

    Returns:
        List of entity names in topological order, or None if graph has cycles
    """
    _check_networkx()

    G = build_networkx_graph(entities, relations, directed=True)

    try:
        return list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        return None  # Graph has cycles


def find_cycles(
    entities: List[Entity],
    relations: List[Relation]
) -> List[List[str]]:
    """Find all simple cycles in the graph.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects

    Returns:
        List of cycles, each cycle is a list of entity names
    """
    _check_networkx()

    G = build_networkx_graph(entities, relations, directed=True)
    return list(nx.simple_cycles(G))


def get_degree_centrality(
    entities: List[Entity],
    relations: List[Relation]
) -> dict:
    """Calculate degree centrality for each entity.

    Args:
        entities: List of Entity objects
        relations: List of Relation objects

    Returns:
        Dict mapping entity name to centrality score (0-1)
    """
    _check_networkx()

    G = build_networkx_graph(entities, relations, directed=False)
    return dict(nx.degree_centrality(G))
