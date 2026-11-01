import * as THREE from 'three';

export interface WallSegmentCollider {
  collider_id: string;
  type: string;
  p0: [number, number, number];
  p1: [number, number, number];
  height_m: number;
  thickness_m: number;
}

export interface FurnitureCollider {
  collider_id: string;
  category: string;
  center_3d: [number, number, number];
  dimensions_m: [number, number, number];
  min_3d: [number, number, number];
  max_3d: [number, number, number];
}

export interface RoomCollisionData {
  room_id: string;
  room_name?: string;
  floor_collider: {
    elevation_z: number;
    boundary_polygon_2d: [number, number][];
  };
  wall_colliders: WallSegmentCollider[];
  furniture_colliders: FurnitureCollider[];
  walkable_boundary_polygon_2d: [number, number][];
}

export interface CollisionResult {
  allowedPosition: THREE.Vector3;
  isColliding: boolean;
  collidedWith?: 'WALL' | 'FURNITURE' | 'BOUNDARY';
  activeRoomId?: string;
  isInDoorway: boolean;
}

export class CollisionSystem {
  private rooms: RoomCollisionData[] = [];
  public playerRadius: number = 0.35; // 35 cm player collision radius
  public playerHeight: number = 1.60; // 1.60m eye-level
  public stepHeight: number = 0.25;   // 25 cm stair step capability
  private lastValidPosition: THREE.Vector3 = new THREE.Vector3(0, 0, 1.60);
  private currentRoomId: string = '';

  constructor(playerRadius: number = 0.35, playerHeight: number = 1.60) {
    this.playerRadius = playerRadius;
    this.playerHeight = playerHeight;
  }

  public setCollisionData(rooms: RoomCollisionData[]) {
    this.rooms = rooms;
    if (rooms.length > 0 && !this.currentRoomId) {
      this.currentRoomId = rooms[0].room_id;
      const poly = rooms[0].walkable_boundary_polygon_2d;
      if (poly && poly.length > 0) {
        const cx = poly.reduce((acc, p) => acc + p[0], 0) / poly.length;
        const cy = poly.reduce((acc, p) => acc + p[1], 0) / poly.length;
        this.lastValidPosition.set(cx, cy, this.playerHeight);
      }
    }
  }

  /**
   * Swept capsule-obstacle collision resolution.
   * Moves player from currentPos toward targetPos, preventing penetration through walls,
   * furniture, or unmapped room boundaries, while allowing seamless passage through open doorways.
   */
  public resolveMovement(currentPos: THREE.Vector3, targetPos: THREE.Vector3): CollisionResult {
    if (this.rooms.length === 0) {
      return {
        allowedPosition: targetPos.clone(),
        isColliding: false,
        isInDoorway: false
      };
    }

    const proposed = targetPos.clone();
    let isColliding = false;
    let collidedWith: 'WALL' | 'FURNITURE' | 'BOUNDARY' | undefined;

    // Determine current containing room or closest room
    const currentRoom = this.findContainingRoom(currentPos) || this.getRoomById(this.currentRoomId) || this.rooms[0];
    this.currentRoomId = currentRoom.room_id;

    // Check if target is inside an inter-room doorway portal
    const inDoorway = this.isPositionInDoorway(proposed);

    // 1. Wall Segment Collisions across all rooms
    for (const room of this.rooms) {
      for (const wall of room.wall_colliders) {
        const p0 = new THREE.Vector2(wall.p0[0], wall.p0[1]);
        const p1 = new THREE.Vector2(wall.p1[0], wall.p1[1]);
        const target2D = new THREE.Vector2(proposed.x, proposed.y);

        // Distance from proposed position to wall line segment
        const distToWall = this.distancePointToSegment(target2D, p0, p1);
        const minDist = this.playerRadius + (wall.thickness_m * 0.5);

        if (distToWall < minDist) {
          isColliding = true;
          collidedWith = 'WALL';

          // Wall normal and tangent
          const wallDir = new THREE.Vector2().subVectors(p1, p0).normalize();
          const wallNormal = new THREE.Vector2(-wallDir.y, wallDir.x);

          // Push player back along collision normal
          const current2D = new THREE.Vector2(currentPos.x, currentPos.y);
          const moveVector = new THREE.Vector2().subVectors(target2D, current2D);

          // Project movement vector onto wall tangent (smooth kinematic sliding)
          const slideMag = moveVector.dot(wallDir);
          const slideVec = wallDir.clone().multiplyScalar(slideMag);

          proposed.x = currentPos.x + slideVec.x;
          proposed.y = currentPos.y + slideVec.y;
        }
      }

      // 2. Furniture AABB Collisions
      for (const furn of room.furniture_colliders) {
        const minX = furn.min_3d[0] - this.playerRadius;
        const maxX = furn.max_3d[0] + this.playerRadius;
        const minY = furn.min_3d[1] - this.playerRadius;
        const maxY = furn.max_3d[1] + this.playerRadius;

        if (proposed.x >= minX && proposed.x <= maxX && proposed.y >= minY && proposed.y <= maxY) {
          isColliding = true;
          collidedWith = 'FURNITURE';

          // Slide along closest axis
          const dLeft = Math.abs(proposed.x - minX);
          const dRight = Math.abs(maxX - proposed.x);
          const dBottom = Math.abs(proposed.y - minY);
          const dTop = Math.abs(maxY - proposed.y);
          const minDelta = Math.min(dLeft, dRight, dBottom, dTop);

          if (minDelta === dLeft || minDelta === dRight) {
            proposed.x = currentPos.x;
          } else {
            proposed.y = currentPos.y;
          }
        }
      }
    }

    // 3. Boundary Restriction (Keep inside room polygon unless passing doorway)
    if (!inDoorway) {
      const targetRoom = this.findContainingRoom(proposed);
      if (!targetRoom) {
        // Target is outside all rooms and not in a doorway -> block movement outside boundary
        isColliding = true;
        collidedWith = 'BOUNDARY';
        proposed.x = currentPos.x;
        proposed.y = currentPos.y;
      } else {
        this.currentRoomId = targetRoom.room_id;
      }
    }

    // 4. Floor Plane Clamping (Z constraint)
    const floorZ = currentRoom.floor_collider?.elevation_z ?? 0.0;
    proposed.z = floorZ + this.playerHeight;

    // 5. Update valid position or trigger out-of-bounds recovery
    if (!isColliding) {
      this.lastValidPosition.copy(proposed);
    } else {
      // If player somehow escaped into invalid void, reset to last valid position
      if (!this.isPositionInsideAnyRoom(proposed) && !inDoorway) {
        proposed.copy(this.lastValidPosition);
      }
    }

    return {
      allowedPosition: proposed,
      isColliding,
      collidedWith,
      activeRoomId: this.currentRoomId,
      isInDoorway: inDoorway
    };
  }

  public getSpawnPositionForRoom(roomId: string): THREE.Vector3 {
    const room = this.getRoomById(roomId) || this.rooms[0];
    if (!room) return new THREE.Vector3(0, 0, this.playerHeight);

    const poly = room.walkable_boundary_polygon_2d;
    if (poly && poly.length > 0) {
      const cx = poly.reduce((acc, p) => acc + p[0], 0) / poly.length;
      const cy = poly.reduce((acc, p) => acc + p[1], 0) / poly.length;
      const fz = room.floor_collider?.elevation_z ?? 0.0;
      return new THREE.Vector3(cx, cy, fz + this.playerHeight);
    }
    return new THREE.Vector3(0, 0, this.playerHeight);
  }

  private findContainingRoom(pos: THREE.Vector3): RoomCollisionData | undefined {
    for (const room of this.rooms) {
      if (this.isPointInPolygon([pos.x, pos.y], room.walkable_boundary_polygon_2d)) {
        return room;
      }
    }
    return undefined;
  }

  private isPositionInsideAnyRoom(pos: THREE.Vector3): boolean {
    return this.findContainingRoom(pos) !== undefined;
  }

  private getRoomById(roomId: string): RoomCollisionData | undefined {
    return this.rooms.find(r => r.room_id === roomId);
  }

  private isPositionInDoorway(pos: THREE.Vector3): boolean {
    // Check if within 0.85m of any inter-room wall boundary opening
    for (const room of this.rooms) {
      for (const wall of room.wall_colliders) {
        if (wall.collider_id.includes('sub')) {
          // Openings between sub-segments indicate doorway threshold
          const midX = (wall.p0[0] + wall.p1[0]) * 0.5;
          const midY = (wall.p0[1] + wall.p1[1]) * 0.5;
          const dist = Math.hypot(pos.x - midX, pos.y - midY);
          if (dist < 1.10) {
            return true;
          }
        }
      }
    }
    return false;
  }

  private distancePointToSegment(p: THREE.Vector2, a: THREE.Vector2, b: THREE.Vector2): number {
    const ab = new THREE.Vector2().subVectors(b, a);
    const ap = new THREE.Vector2().subVectors(p, a);
    const lenSq = ab.lengthSq();
    if (lenSq === 0) return ap.length();
    const t = Math.max(0, Math.min(1, ap.dot(ab) / lenSq));
    const proj = a.clone().add(ab.multiplyScalar(t));
    return p.distanceTo(proj);
  }

  private isPointInPolygon(point: [number, number], polygon: [number, number][]): boolean {
    if (!polygon || polygon.length < 3) return true;
    let inside = false;
    const x = point[0], y = point[1];
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const xi = polygon[i][0], yi = polygon[i][1];
      const xj = polygon[j][0], yj = polygon[j][1];
      const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  }
}

