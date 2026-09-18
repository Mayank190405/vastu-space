import * as THREE from 'three';

export interface ARNavigationState {
  hasCamera: boolean;
  cameraError?: string;
  compassHeading: number;
  bearingToTarget: number;
  distanceToTarget: number;
  turnDirection: 'straight' | 'slight-left' | 'slight-right' | 'sharp-left' | 'sharp-right' | 'behind';
}

export class MobileARNavigationController {
  private videoElement: HTMLVideoElement;
  private stream: MediaStream | null = null;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private arrowGroup = new THREE.Group();

  private compassHeading = 0; // Degrees 0-360
  private targetBearing = 45; // Simulated initial target bearing
  private distanceToTarget = 4.2;

  private onStateChange?: (state: ARNavigationState) => void;
  private animId?: number;

  constructor(
    container: HTMLElement,
    onStateChange?: (state: ARNavigationState) => void
  ) {
    this.onStateChange = onStateChange;

    // 1. Create Background Video Stream Element
    const video = document.createElement('video');
    video.autoplay = true;
    video.playsInline = true;
    video.muted = true;
    video.style.position = 'absolute';
    video.style.top = '0';
    video.style.left = '0';
    video.style.width = '100%';
    video.style.height = '100%';
    video.style.objectFit = 'cover';
    video.style.zIndex = '1';
    container.appendChild(video);
    this.videoElement = video;

    // 2. Create Transparent Three.js AR Canvas
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 100);
    this.camera.position.set(0, 0, 2.5);

    this.renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.domElement.style.position = 'absolute';
    this.renderer.domElement.style.top = '0';
    this.renderer.domElement.style.left = '0';
    this.renderer.domElement.style.width = '100%';
    this.renderer.domElement.style.height = '100%';
    this.renderer.domElement.style.zIndex = '2';
    this.renderer.domElement.style.pointerEvents = 'none';
    container.appendChild(this.renderer.domElement);

    // 3. Build 3D Directional AR Guidance Arrow
    this.build3DArrow();

    // 4. Start Camera Stream
    this.startCameraStream();

    // 5. Setup Device Orientation / Gyro
    this.setupOrientationListener();

    // 6. Animation Loop
    this.animate();
  }

  private build3DArrow() {
    this.arrowGroup = new THREE.Group();
    this.arrowGroup.position.set(0, -0.4, 0);

    // Golden arrow body
    const shaftGeom = new THREE.CylinderGeometry(0.08, 0.08, 0.7, 32);
    const goldMat = new THREE.MeshStandardMaterial({
      color: 0xdfb873,
      emissive: 0x8c6d23,
      emissiveIntensity: 0.4,
      metalness: 0.8,
      roughness: 0.2
    });
    const shaft = new THREE.Mesh(shaftGeom, goldMat);
    shaft.position.y = 0.35;
    this.arrowGroup.add(shaft);

    // Arrowhead cone
    const headGeom = new THREE.ConeGeometry(0.24, 0.45, 32);
    const head = new THREE.Mesh(headGeom, goldMat);
    head.position.y = 0.85;
    this.arrowGroup.add(head);

    // Floating pulsing ring around arrow
    const ringGeom = new THREE.TorusGeometry(0.4, 0.02, 16, 64);
    ringGeom.rotateX(Math.PI / 2);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x10b981,
      transparent: true,
      opacity: 0.7
    });
    const ring = new THREE.Mesh(ringGeom, ringMat);
    ring.position.y = 0.35;
    ring.name = 'ar_ring';
    this.arrowGroup.add(ring);

    // Add ambient and directional light to AR scene
    const ambLight = new THREE.AmbientLight(0xffffff, 1.2);
    this.scene.add(ambLight);

    const dirLight = new THREE.DirectionalLight(0xffeedd, 1.5);
    dirLight.position.set(2, 4, 3);
    this.scene.add(dirLight);

    this.scene.add(this.arrowGroup);
  }

  private async startCameraStream() {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: 'environment' },
            width: { ideal: 1920 },
            height: { ideal: 1080 }
          },
          audio: false
        });
        this.stream = stream;
        this.videoElement.srcObject = stream;
        await this.videoElement.play();
        this.emitState(true);
      } else {
        this.emitState(false, 'MediaDevices camera API not supported in browser');
      }
    } catch (err: any) {
      console.warn('Camera feed error or permission denied:', err);
      this.emitState(false, err?.message || 'Camera permission denied');
    }
  }

  private setupOrientationListener() {
    const handleOrientation = (event: DeviceOrientationEvent) => {
      if (event.alpha !== null) {
        // alpha: 0 to 360 degrees (compass north is usually 360 - alpha on iOS/Android)
        const heading = (event as any).webkitCompassHeading !== undefined
          ? (event as any).webkitCompassHeading
          : (360 - event.alpha) % 360;
        this.compassHeading = Math.round(heading);
      }
    };

    if (typeof (DeviceOrientationEvent as any)?.requestPermission === 'function') {
      // iOS 13+ permission workflow
      (DeviceOrientationEvent as any).requestPermission()
        .then((response: string) => {
          if (response === 'granted') {
            window.addEventListener('deviceorientation', handleOrientation, true);
          }
        })
        .catch(() => {});
    } else {
      window.addEventListener('deviceorientation', handleOrientation, true);
    }
  }

  public setTargetLocation(bearing: number, distance: number) {
    this.targetBearing = bearing;
    this.distanceToTarget = distance;
  }

  private animate = () => {
    this.animId = requestAnimationFrame(this.animate);
    const time = performance.now() * 0.001;

    // Relative angle between current heading and target POI
    let relativeAngle = (this.targetBearing - this.compassHeading + 360) % 360;
    if (relativeAngle > 180) relativeAngle -= 360;

    // Smoothly rotate the 3D arrow to point toward target bearing
    const targetRad = THREE.MathUtils.degToRad(-relativeAngle);
    this.arrowGroup.rotation.z += (targetRad - this.arrowGroup.rotation.z) * 0.15;
    this.arrowGroup.position.y = -0.35 + Math.sin(time * 3.0) * 0.04;

    const ring = this.arrowGroup.getObjectByName('ar_ring');
    if (ring) {
      ring.scale.setScalar(1.0 + Math.sin(time * 4.0) * 0.15);
    }

    this.renderer.render(this.scene, this.camera);
    this.emitState(true);
  };

  private emitState(hasCamera: boolean, error?: string) {
    if (!this.onStateChange) return;

    let relativeAngle = (this.targetBearing - this.compassHeading + 360) % 360;
    if (relativeAngle > 180) relativeAngle -= 360;

    let turnDirection: ARNavigationState['turnDirection'] = 'straight';
    if (Math.abs(relativeAngle) <= 15) {
      turnDirection = 'straight';
    } else if (relativeAngle > 15 && relativeAngle <= 60) {
      turnDirection = 'slight-right';
    } else if (relativeAngle > 60 && relativeAngle <= 135) {
      turnDirection = 'sharp-right';
    } else if (relativeAngle < -15 && relativeAngle >= -60) {
      turnDirection = 'slight-left';
    } else if (relativeAngle < -60 && relativeAngle >= -135) {
      turnDirection = 'sharp-left';
    } else {
      turnDirection = 'behind';
    }

    this.onStateChange({
      hasCamera,
      cameraError: error,
      compassHeading: this.compassHeading,
      bearingToTarget: this.targetBearing,
      distanceToTarget: this.distanceToTarget,
      turnDirection
    });
  }

  public dispose() {
    if (this.animId) cancelAnimationFrame(this.animId);
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
    }
    if (this.videoElement.parentElement) {
      this.videoElement.parentElement.removeChild(this.videoElement);
    }
    if (this.renderer.domElement.parentElement) {
      this.renderer.domElement.parentElement.removeChild(this.renderer.domElement);
    }
    this.renderer.dispose();
  }
}
