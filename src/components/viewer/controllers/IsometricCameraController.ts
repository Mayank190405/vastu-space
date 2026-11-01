import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export class IsometricCameraController {
  private camera: THREE.PerspectiveCamera;
  private domElement: HTMLElement;
  public controls: OrbitControls;
  private savedWalkingPosition = new THREE.Vector3(0, 0, 1.6);
  private savedWalkingTarget = new THREE.Vector3(0, 5, 1.6);

  constructor(camera: THREE.PerspectiveCamera, domElement: HTMLElement) {
    this.camera = camera;
    this.domElement = domElement;

    this.controls = new OrbitControls(this.camera, this.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.maxPolarAngle = Math.PI / 2.15; // Don't go below floor level
    this.controls.minDistance = 3.0;
    this.controls.maxDistance = 50.0;
    this.controls.enabled = false;
  }

  public activateIsometricView(centerTarget: THREE.Vector3 = new THREE.Vector3(0, 0, 0), lastWalkPos?: THREE.Vector3) {
    if (lastWalkPos) {
      this.savedWalkingPosition.copy(lastWalkPos);
      const dir = new THREE.Vector3();
      this.camera.getWorldDirection(dir);
      this.savedWalkingTarget.copy(lastWalkPos).add(dir);
    }

    this.controls.enabled = true;
    this.controls.target.copy(centerTarget);

    // Elevated 45-degree isometric position
    const elevation = 14.0;
    const distance = 16.0;
    this.camera.position.set(
      centerTarget.x - distance * 0.707,
      centerTarget.y - distance * 0.707,
      centerTarget.z + elevation
    );
    this.camera.lookAt(centerTarget);
    this.controls.update();
  }

  public focusOnRoom(roomCenter: THREE.Vector3) {
    this.controls.target.set(roomCenter.x, roomCenter.y, 0.0);
    this.camera.position.set(
      roomCenter.x - 8.0,
      roomCenter.y - 8.0,
      10.0
    );
    this.camera.lookAt(roomCenter.x, roomCenter.y, 0.0);
    this.controls.update();
  }

  public getSavedWalkingPosition(): THREE.Vector3 {
    return this.savedWalkingPosition.clone();
  }

  public getSavedWalkingTarget(): THREE.Vector3 {
    return this.savedWalkingTarget.clone();
  }

  public deactivate() {
    this.controls.enabled = false;
  }

  public update() {
    if (this.controls.enabled) {
      this.controls.update();
    }
  }

  public dispose() {
    this.controls.dispose();
  }
}

