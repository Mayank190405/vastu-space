import { NavMeshGraph } from '../services/NavigationSystem';

export interface NavmeshValidationResult {
  isFullyConnected: boolean;
  totalNodes: number;
  totalEdges: number;
  doorwayPortalsCount: number;
  unreachableNodes: string[];
  adaCompliantRatio: number;
}

export class NavmeshConnectivityValidator {
  public static validate(graph: NavMeshGraph): NavmeshValidationResult {
    if (!graph || !graph.nodes || graph.nodes.length === 0) {
      return {
        isFullyConnected: false,
        totalNodes: 0,
        totalEdges: 0,
        doorwayPortalsCount: 0,
        unreachableNodes: [],
        adaCompliantRatio: 1.0
      };
    }

    const nodeIds = new Set(graph.nodes.map(n => n.node_id));
    const adjacency: Map<string, string[]> = new Map();
    for (const nid of nodeIds) {
      adjacency.set(nid, []);
    }

    let doorwayCount = 0;
    for (const edge of graph.edges) {
      if (edge.is_doorway) doorwayCount++;
      adjacency.get(edge.source_node)?.push(edge.target_node);
      adjacency.get(edge.target_node)?.push(edge.source_node);
    }

    // Traverse from first node using BFS
    const startNode = graph.nodes[0].node_id;
    const visited = new Set<string>([startNode]);
    const queue = [startNode];

    while (queue.length > 0) {
      const curr = queue.shift()!;
      const neighbors = adjacency.get(curr) || [];
      for (const next of neighbors) {
        if (!visited.has(next)) {
          visited.add(next);
          queue.push(next);
        }
      }
    }

    const unreachable = graph.nodes
      .filter(n => !visited.has(n.node_id))
      .map(n => n.node_id);

    const accessibleNodes = graph.nodes.filter(n => n.is_accessible).length;
    const adaRatio = accessibleNodes / Math.max(graph.nodes.length, 1);

    return {
      isFullyConnected: unreachable.length === 0,
      totalNodes: graph.nodes.length,
      totalEdges: graph.edges.length,
      doorwayPortalsCount: doorwayCount,
      unreachableNodes: unreachable,
      adaCompliantRatio: Math.round(adaRatio * 100) / 100
    };
  }
}

