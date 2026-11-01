import * as THREE from 'three';

export interface NavNode {
  node_id: string;
  room_id: string;
  type: string;
  position_3d: [number, number, number];
  is_accessible: boolean;
}

export interface NavEdge {
  edge_id: string;
  source_node: string;
  target_node: string;
  distance_m: number;
  is_doorway: boolean;
}

export interface NavMeshGraph {
  status: string;
  agent_radius_m: number;
  node_count: number;
  edge_count: number;
  nodes: NavNode[];
  edges: NavEdge[];
}

export class NavigationSystem {
  private navmesh: NavMeshGraph | null = null;
  private nodeMap: Map<string, NavNode> = new Map();
  private adjacency: Map<string, { target: string; distance: number; isDoor: boolean }[]> = new Map();

  public loadNavMesh(graph: NavMeshGraph) {
    this.navmesh = graph;
    this.nodeMap.clear();
    this.adjacency.clear();

    for (const node of graph.nodes) {
      this.nodeMap.set(node.node_id, node);
      this.adjacency.set(node.node_id, []);
    }

    for (const edge of graph.edges) {
      this.adjacency.get(edge.source_node)?.push({
        target: edge.target_node,
        distance: edge.distance_m,
        isDoor: edge.is_doorway
      });
      this.adjacency.get(edge.target_node)?.push({
        target: edge.source_node,
        distance: edge.distance_m,
        isDoor: edge.is_doorway
      });
    }
  }

  /**
   * Computes shortest waypoint path between two 3D positions using A* on the navigation graph.
   */
  public findPath(startPos: THREE.Vector3, endPos: THREE.Vector3): THREE.Vector3[] {
    if (!this.navmesh || this.nodeMap.size === 0) {
      return [startPos.clone(), endPos.clone()];
    }

    const startNode = this.findClosestNode(startPos);
    const endNode = this.findClosestNode(endPos);

    if (!startNode || !endNode) {
      return [startPos.clone(), endPos.clone()];
    }

    if (startNode.node_id === endNode.node_id) {
      return [startPos.clone(), endPos.clone()];
    }

    // A* algorithm
    const openSet: string[] = [startNode.node_id];
    const cameFrom: Map<string, string> = new Map();
    const gScore: Map<string, number> = new Map();
    const fScore: Map<string, number> = new Map();

    for (const nid of this.nodeMap.keys()) {
      gScore.set(nid, Infinity);
      fScore.set(nid, Infinity);
    }

    gScore.set(startNode.node_id, 0);
    fScore.set(startNode.node_id, this.heuristic(startNode, endNode));

    while (openSet.length > 0) {
      // Node in openSet with lowest fScore
      openSet.sort((a, b) => (fScore.get(a) || Infinity) - (fScore.get(b) || Infinity));
      const current = openSet.shift()!;

      if (current === endNode.node_id) {
        // Reconstruct path
        const path: THREE.Vector3[] = [endPos.clone()];
        let curr = current;
        while (cameFrom.has(curr)) {
          const n = this.nodeMap.get(curr)!;
          path.unshift(new THREE.Vector3(n.position_3d[0], n.position_3d[1], n.position_3d[2] + 0.1));
          curr = cameFrom.get(curr)!;
        }
        path.unshift(startPos.clone());
        return path;
      }

      const neighbors = this.adjacency.get(current) || [];
      for (const edge of neighbors) {
        const neighborNode = this.nodeMap.get(edge.target);
        if (!neighborNode || !neighborNode.is_accessible) continue;

        const tentativeG = (gScore.get(current) || Infinity) + edge.distance;
        if (tentativeG < (gScore.get(edge.target) || Infinity)) {
          cameFrom.set(edge.target, current);
          gScore.set(edge.target, tentativeG);
          fScore.set(edge.target, tentativeG + this.heuristic(neighborNode, endNode));

          if (!openSet.includes(edge.target)) {
            openSet.push(edge.target);
          }
        }
      }
    }

    return [startPos.clone(), endPos.clone()];
  }

  private findClosestNode(pos: THREE.Vector3): NavNode | null {
    let closest: NavNode | null = null;
    let minDist = Infinity;

    for (const node of this.nodeMap.values()) {
      const d = Math.hypot(pos.x - node.position_3d[0], pos.y - node.position_3d[1]);
      if (d < minDist) {
        minDist = d;
        closest = node;
      }
    }
    return closest;
  }

  private heuristic(a: NavNode, b: NavNode): number {
    return Math.hypot(
      a.position_3d[0] - b.position_3d[0],
      a.position_3d[1] - b.position_3d[1]
    );
  }
}

