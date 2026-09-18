import * as THREE from 'three';
import { PointerLockControls } from 'three/examples/jsm/controls/PointerLockControls.js';

export interface RoamingState {
  isLocked: boolean;
  isColliding: boolean;
  isSprinting: boolean;
  currentHeight: number;
}

export class FirstPersonRoamingController {
  private camera: THREE.PerspectiveCamera;
  private domElement: HTMLElement;
  public controls: PointerLockControls;
  private scene: THREE.Scene;

  // Movement keys
  private moveForward = false;
  private moveBackward = false;
  private moveLeft = false;
  private moveRight = false;
  private isSprinting = false;

  // Physics & Kinematics
  private velocity = new THREE.Vector3();
  private direction = new THREE.Vector3();
  private prevTime = performance.now();
  private eyeHeight = 1.6; // Metric eye-level: 1.60 meters
  private playerRadius = 0.35; // Collision cylinder radius: 35 cm

  // Floor and obstacles
  private collidableObjects: THREE.Object3D[] = [];
  private floorRaycaster = new THREE.Raycaster();
  private wallRaycaster = new THREE.Raycaster();

  // State callback
  private onStateChange?: (state: RoamingState) => void;
  private isColliding = false;

  constructor(
    camera: THREE.PerspectiveCamera,
    domElement: HTMLElement,
    scene: THREE.Scene,
    onStateChange?: (state: RoamingState) => void
  ) {
    this.camera = camera;
    this.domElement = domElement;
    this.scene = scene;
    this.onStateChange = onStateChange;

    this.controls = new PointerLockControls(this.camera, this.domElement);

    this.setupEventListeners();
  }

  public setCollidableObjects(objects: THREE.Object3D[]) {
    this.collidableObjects = objects;
  }

  private setupEventListeners() {
    this.controls.addEventListener('lock', () => {
      this.emitState();
    });

    this.controls.addEventListener('unlock', () => {
      this.moveForward = false;
      this.moveBackward = false;
      this.moveLeft = false;
      this.moveRight = false;
      this.isSprinting = false;
      this.isColliding = false;
      this.emitState();
    });

    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);
  }

  public lock() {
    this.controls.lock();
  }

  public unlock() {
    this.controls.unlock();
  }

  public isLocked(): boolean {
    return this.controls.isLocked;
  }

  private handleKeyDown = (event: KeyboardEvent) => {
    if (!this.controls.isLocked) return;

    switch (event.code) {
      case 'ArrowUp':
      case 'KeyW':
        this.moveForward = true;
        break;
      case 'ArrowLeft':
      case 'KeyA':
        this.moveLeft = true;
        break;
      case 'ArrowDown':
      case 'KeyS':
        this.moveBackward = true;
        break;
      case 'ArrowRight':
      case 'KeyD':
        this.moveRight = true;
        break;
      case 'ShiftLeft':
      case 'ShiftRight':
        this.isSprinting = true;
        this.emitState();
        break;
    }
  };

  private handleKeyUp = (event: KeyboardEvent) => {
    switch (event.code) {
      case 'ArrowUp':
      case 'KeyW':
        this.moveForward = false;
        break;
      case 'ArrowLeft':
      case 'KeyA':
        this.moveLeft = false;
        break;
      case 'ArrowDown':
      case 'KeyS':
        this.moveBackward = false;
        break;
      case 'ArrowRight':
      case 'KeyD':
        this.moveRight = false;
        break;
      case 'ShiftLeft':
      case 'ShiftRight':
        this.isSprinting = false;
        this.emitState();
        break;
    }
  };

  public update(): void {
    if (!this.controls.isLocked) return;

    const time = performance.now();
    const delta = Math.min((time - this.prevTime) / 1000, 0.1);
    this.prevTime = time;

    // Deceleration damping
    this.velocity.x -= this.velocity.x * 10.0 * delta;
    this.velocity.z -= this.velocity.z * 10.0 * delta;

    // Movement direction
    this.direction.z = Number(this.moveForward) - Number(this.moveBackward);
    this.direction.x = Number(this.moveRight) - Number(this.moveLeft);
    this.direction.normalize();

    // Speed: 2.2 m/s walk, 4.8 m/s sprint
    const baseSpeed = this.isSprinting ? 45.0 : 22.0;

    if (this.moveForward || this.moveBackward) {
      this.velocity.z -= this.direction.z * baseSpeed * delta;
    }
    if (this.moveLeft || this.moveRight) {
      this.velocity.x -= this.direction.x * baseSpeed * delta;
    }

    // Proposed displacement
    const moveX = -this.velocity.x * delta;
    const moveZ = -this.velocity.z * delta;

    // Obstacle & Wall Collision Check
    let collided = false;
    if (Math.abs(moveX) > 0.0001 || Math.abs(moveZ) > 0.0001) {
      const currentPos = this.camera.position.clone();
      const horizontalDir = new THREE.Vector3();
      this.camera.getWorldDirection(horizontalDir);
      horizontalDir.y = 0;
      horizontalDir.normalize();

      const lateralDir = new THREE.Vector3(-horizontalDir.z, 0, horizontalDir.x);

      // Compute intended movement vector in world space
      const intendedMove = new THREE.Vector3()
        .addScaledVector(horizontalDir, -moveZ)
        .addScaledVector(lateralDir, moveX);

      if (intendedMove.lengthSq() > 0.0001) {
        const rayDir = intendedMove.clone().normalize();
        const waistHeight = currentPos.y - 0.7; // Check at waist/torso height
        const rayOrigin = new THREE.Vector3(currentPos.x, waistHeight, currentPos.z);

        this.wallRaycaster.set(rayOrigin, rayDir);
        this.wallRaycaster.far = this.playerRadius + intendedMove.length() + 0.15;

        const wallHits = this.wallRaycaster.intersectObjects(this.collidableObjects, true);
        if (wallHits.length > 0 && wallHits[0].distance < this.playerRadius + 0.1) {
          collided = true;
        }
      }
    }

    if (collided) {
      this.isColliding = true;
      // Stop horizontal velocity on collision to prevent penetration
      this.velocity.x = 0;
      this.velocity.z = 0;
    } else {
      this.isColliding = false;
      this.controls.moveRight(moveX);
      this.controls.moveForward(-moveZ);
    }

    // Floor Snapping / Height Constraint
    const playerPos = this.camera.position;
    const rayStart = new THREE.Vector3(playerPos.x, playerPos.y + 2.0, playerPos.z);
    this.floorRaycaster.set(rayStart, new THREE.Vector3(0, -1, 0));
    this.floorRaycaster.far = 10.0;

    const floorHits = this.floorRaycaster.intersectObjects(this.collidableObjects, true);
    if (floorHits.length > 0) {
      const floorY = floorHits[0].point.y;
      const targetEyeY = floorY + this.eyeHeight;
      // Smooth damp vertical snapping
      playerPos.y += (targetEyeY - playerPos.y) * 0.25;
    } else {
      // Fallback: stay grounded at base level Y = 0.0 + 1.6m
      const defaultEyeY = 1.6;
      playerPos.y += (defaultEyeY - playerPos.y) * 0.25;
    }

    this.emitState();
  }

  private emitState() {
    if (this.onStateChange) {
      this.onStateChange({
        isLocked: this.controls.isLocked,
        isColliding: this.isColliding,
        isSprinting: this.isSprinting,
        currentHeight: this.camera.position.y
      });
    }
  }

  public dispose() {
    window.removeEventListener('keydown', this.handleKeyDown);
    window.removeEventListener('keyup', this.handleKeyUp);
    this.controls.dispose();
  }
}
