import * as THREE from 'three';
import { CollisionSystem, RoomCollisionData } from '../services/CollisionSystem';

export interface CollisionTestReport {
  totalTests: number;
  passedCount: number;
  failedCount: number;
  wallPenetrationBlockedRatio: number;
  doorwaysTraversableRatio: number;
  furnitureObstaclesBlockedRatio: number;
  allPassed: boolean;
  failures: string[];
}

export class CollisionRegressionTests {
  /**
   * Executes programmatic kinematic test rays against every structural wall and obstacle.
   */
  public static runTests(
    collisionSystem: CollisionSystem,
    rooms: RoomCollisionData[]
  ): CollisionTestReport {
    let total = 0;
    let passed = 0;
    const failures: string[] = [];

    let wallTests = 0;
    let wallBlocked = 0;
    let doorTests = 0;
    let doorPassed = 0;
    let furnTests = 0;
    let furnBlocked = 0;

    for (const room of rooms) {
      const poly = room.walkable_boundary_polygon_2d;
      if (!poly || poly.length < 3) continue;

      const centerX = poly.reduce((acc, p) => acc + p[0], 0) / poly.length;
      const centerY = poly.reduce((acc, p) => acc + p[1], 0) / poly.length;
      const center = new THREE.Vector3(centerX, centerY, 1.60);

      // 1. Wall Penetration Tests
      for (const wall of room.wall_colliders) {
        total++;
        wallTests++;
        const p0 = new THREE.Vector2(wall.p0[0], wall.p0[1]);
        const p1 = new THREE.Vector2(wall.p1[0], wall.p1[1]);
        const midWall = new THREE.Vector2().addVectors(p0, p1).multiplyScalar(0.5);

        // Compute outward normal
        const wallDir = new THREE.Vector2().subVectors(p1, p0).normalize();
        let normal = new THREE.Vector2(-wallDir.y, wallDir.x);

        const fromCenter = new THREE.Vector2().subVectors(midWall, new THREE.Vector2(centerX, centerY));
        if (normal.dot(fromCenter) < 0) {
          normal.negate();
        }

        // Attempt to move from slightly inside room through the wall to 0.6m beyond it
        const start = new THREE.Vector3(midWall.x - normal.x * 0.20, midWall.y - normal.y * 0.20, 1.60);
        const target = new THREE.Vector3(midWall.x + normal.x * 0.60, midWall.y + normal.y * 0.60, 1.60);

        const res = collisionSystem.resolveMovement(start, target);
        const distBeyond = new THREE.Vector2(res.allowedPosition.x - midWall.x, res.allowedPosition.y - midWall.y).dot(normal);

        // Player must NOT be allowed to penetrate past the wall surface!
        if (res.isColliding && distBeyond <= 0.05) {
          passed++;
          wallBlocked++;
        } else {
          failures.push(`Wall ${wall.collider_id} allowed penetration (distBeyond: ${distBeyond.toFixed(3)}m)`);
        }
      }

      // 2. Furniture Obstacle Tests
      for (const furn of room.furniture_colliders) {
        total++;
        furnTests++;
        const fc = new THREE.Vector3(furn.center_3d[0], furn.center_3d[1], 1.60);
        const start = new THREE.Vector3(fc.x - 1.0, fc.y, 1.60);
        const target = fc.clone(); // Aim right at the center of the sofa/table

        const res = collisionSystem.resolveMovement(start, target);
        // Player must NOT reach center of furniture
        const distToCenter = Math.hypot(res.allowedPosition.x - fc.x, res.allowedPosition.y - fc.y);
        if (res.isColliding && distToCenter >= collisionSystem.playerRadius * 0.5) {
          passed++;
          furnBlocked++;
        } else {
          failures.push(`Furniture ${furn.collider_id} failed to block movement to center`);
        }
      }
    }

    const wallRatio = wallTests > 0 ? wallBlocked / wallTests : 1.0;
    const furnRatio = furnTests > 0 ? furnBlocked / furnTests : 1.0;
    const doorRatio = doorTests > 0 ? doorPassed / doorTests : 1.0;
    const allPassed = failures.length === 0;

    return {
      totalTests: total,
      passedCount: passed,
      failedCount: failures.length,
      wallPenetrationBlockedRatio: Math.round(wallRatio * 100) / 100,
      doorwaysTraversableRatio: Math.round(doorRatio * 100) / 100,
      furnitureObstaclesBlockedRatio: Math.round(furnRatio * 100) / 100,
      allPassed,
      failures
    };
  }
}

