import * as THREE from 'three';
import { PointerLockControls } from 'three/examples/jsm/controls/PointerLockControls.js';
import { CollisionSystem, CollisionResult } from '../services/CollisionSystem';

export interface FirstPersonState {
  isLocked: boolean;
  isColliding: boolean;
  collidedWith?: string;
  isSprinting: boolean;
  activeRoomId: string;
  isInDoorway: boolean;
  playerCoords: { x: number; y: number; z: number };
}

export class FirstPersonController {
  private camera: THREE.PerspectiveCamera;
  private domElement: HTMLElement;
  public controls: PointerLockControls;
  private collisionSystem: CollisionSystem;

  // Key states
  private moveForward = false;
  private moveBackward = false;
  private moveLeft = false;
  private moveRight = false;
  private isSprinting = false;

  // Mobile virtual joystick input
  public virtualInput = { x: 0, y: 0 };

  // Kinematics
  private velocity = new THREE.Vector3();
  private prevTime = performance.now();
  private baseSpeed = 2.4;    // 2.4 m/s walking speed
  private sprintSpeed = 4.2;  // 4.2 m/s sprint speed

  private onStateChange?: (state: FirstPersonState) => void;
  private onModeToggleRequested?: () => void;

  private latestCollisionResult?: CollisionResult;

  constructor(
    camera: THREE.PerspectiveCamera,
    domElement: HTMLElement,
    collisionSystem: CollisionSystem,
    onStateChange?: (state: FirstPersonState) => void,
    onModeToggleRequested?: () => void
  ) {
    this.camera = camera;
    this.domElement = domElement;
    this.collisionSystem = collisionSystem;
    this.onStateChange = onStateChange;
    this.onModeToggleRequested = onModeToggleRequested;

    this.controls = new PointerLockControls(this.camera, this.domElement);
    this.setupEventListeners();
  }

  private setupEventListeners() {
    this.controls.addEventListener('lock', () => this.emitState());
    this.controls.addEventListener('unlock', () => {
      this.moveForward = false;
      this.moveBackward = false;
      this.moveLeft = false;
      this.moveRight = false;
      this.isSprinting = false;
      this.emitState();
    });

    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);
  }

  public dispose() {
    this.controls.unlock();
    this.controls.dispose();
    window.removeEventListener('keydown', this.handleKeyDown);
    window.removeEventListener('keyup', this.handleKeyUp);
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

  public setPosition(pos: THREE.Vector3) {
    this.camera.position.copy(pos);
  }

  public getPosition(): THREE.Vector3 {
    return this.camera.position.clone();
  }

  private handleKeyDown = (event: KeyboardEvent) => {
    // Mode toggle shortcut 'V' works even if unlocked
    if (event.code === 'KeyV' && !event.repeat) {
      this.onModeToggleRequested?.();
      return;
    }

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
        break;
    }
  };

  public update(): CollisionResult {
    const time = performance.now();
    const delta = Math.min((time - this.prevTime) / 1000.0, 0.1);
    this.prevTime = time;

    // Movement damping
    this.velocity.x -= this.velocity.x * 10.0 * delta;
    this.velocity.y -= this.velocity.y * 10.0 * delta;

    // Evaluate input vector
    let inputForward = Number(this.moveForward) - Number(this.moveBackward);
    let inputSide = Number(this.moveRight) - Number(this.moveLeft);

    // Add mobile virtual joystick input if present
    if (Math.abs(this.virtualInput.y) > 0.05) inputForward += this.virtualInput.y;
    if (Math.abs(this.virtualInput.x) > 0.05) inputSide += this.virtualInput.x;

    const moveSpeed = this.isSprinting ? this.sprintSpeed : this.baseSpeed;

    if (inputForward !== 0 || inputSide !== 0) {
      const inputDir = new THREE.Vector2(inputSide, inputForward).normalize();
      this.velocity.x += inputDir.x * moveSpeed * 10.0 * delta;
      this.velocity.y += inputDir.y * moveSpeed * 10.0 * delta;
    }

    // Compute proposed step
    const currentPos = this.camera.position.clone();
    const targetPos = currentPos.clone();

    // Transform local camera movement to world horizontal plane
    const forward = new THREE.Vector3();
    this.camera.getWorldDirection(forward);
    forward.z = 0; // Horizontal ground movement only
    forward.normalize();

    const right = new THREE.Vector3();
    right.crossVectors(this.camera.up, forward).normalize();

    targetPos.addScaledVector(forward, this.velocity.y * delta);
    targetPos.addScaledVector(right, -this.velocity.x * delta);

    // Collision detection & resolution
    const collisionRes = this.collisionSystem.resolveMovement(currentPos, targetPos);
    this.camera.position.copy(collisionRes.allowedPosition);
    this.latestCollisionResult = collisionRes;

    this.emitState();
    return collisionRes;
  }

  private emitState() {
    this.onStateChange?.({
      isLocked: this.controls.isLocked,
      isColliding: this.latestCollisionResult?.isColliding ?? false,
      collidedWith: this.latestCollisionResult?.collidedWith,
      isSprinting: this.isSprinting,
      activeRoomId: this.latestCollisionResult?.activeRoomId ?? '',
      isInDoorway: this.latestCollisionResult?.isInDoorway ?? false,
      playerCoords: {
        x: Math.round(this.camera.position.x * 100) / 100,
        y: Math.round(this.camera.position.y * 100) / 100,
        z: Math.round(this.camera.position.z * 100) / 100
      }
    });
  }
}

