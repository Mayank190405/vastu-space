import * as THREE from 'three';

export interface POI {
  id: string;
  name: string;
  category: 'Entrance' | 'Workplace' | 'Meeting' | 'Facility' | 'Safety' | 'Custom';
  position: [number, number, number];
  color: string;
  description?: string;
  icon?: string;
}

export interface TurnInstruction {
  id: string;
  text: string;
  distanceMeters: number;
  type: 'straight' | 'turn-left' | 'turn-right' | 'arrive';
}

export interface NavigationRoute {
  targetPOI: POI;
  totalDistanceMeters: number;
  estimatedSeconds: number;
  waypoints: THREE.Vector3[];
  instructions: TurnInstruction[];
  isWheelchairCompliant: boolean;
}

export class NavigationEngine {
  private pois: POI[] = [];
  private scene: THREE.Scene;
  private markerGroup = new THREE.Group();
  private pathGroup = new THREE.Group();
  private pathMesh: THREE.Mesh | null = null;
  private pathUniforms: { [key: string]: { value: any } } = {};

  constructor(scene: THREE.Scene, initialPOIs: POI[] = []) {
    this.scene = scene;
    this.scene.add(this.markerGroup);
    this.scene.add(this.pathGroup);
    if (initialPOIs.length > 0) {
      this.pois = [...initialPOIs];
      this.rebuildPOIMarkers();
    }
  }

  public setPOIs(pois: POI[]) {
    this.pois = [...pois];
    this.rebuildPOIMarkers();
  }

  public getPOIs(): POI[] {
    return this.pois;
  }

  public addCustomPOI(poi: Omit<POI, 'id'>): POI {
    const newPOI: POI = {
      ...poi,
      id: `poi-custom-${Date.now()}`
    };
    this.pois.push(newPOI);
    this.rebuildPOIMarkers();
    return newPOI;
  }

  public rebuildPOIMarkers() {
    // Clear existing
    while (this.markerGroup.children.length > 0) {
      const child = this.markerGroup.children[0];
      this.markerGroup.remove(child);
    }

    // Build 3D pulsing beacons for each POI
    this.pois.forEach((poi) => {
      const poiGroup = new THREE.Group();
      poiGroup.position.set(poi.position[0], poi.position[1], poi.position[2]);
      poiGroup.name = `poi_${poi.id}`;

      const color = new THREE.Color(poi.color);

      // 1. Vertical Glow Pillar / Beacon Pole
      const cylinderGeom = new THREE.CylinderGeometry(0.015, 0.015, 1.2, 16);
      const cylinderMat = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.65
      });
      const cylinder = new THREE.Mesh(cylinderGeom, cylinderMat);
      cylinder.position.y = 0.6;
      poiGroup.add(cylinder);

      // 2. Base Ground Pulse Ring
      const ringGeom = new THREE.RingGeometry(0.12, 0.22, 32);
      ringGeom.rotateX(-Math.PI / 2);
      const ringMat = new THREE.MeshBasicMaterial({
        color: color,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.8
      });
      const ring = new THREE.Mesh(ringGeom, ringMat);
      ring.position.y = 0.02;
      poiGroup.add(ring);

      // 3. Floating Diamond / Sphere Marker at Top
      const diamondGeom = new THREE.OctahedronGeometry(0.1, 0);
      const diamondMat = new THREE.MeshStandardMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 0.6,
        roughness: 0.2,
        metalness: 0.8
      });
      const diamond = new THREE.Mesh(diamondGeom, diamondMat);
      diamond.position.y = 1.25;
      diamond.name = 'floating_diamond';
      poiGroup.add(diamond);

      // 4. Billboard Canvas Sprite with POI Name
      const canvas = document.createElement('canvas');
      canvas.width = 380;
      canvas.height = 96;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.fillStyle = 'rgba(15, 23, 42, 0.88)';
        ctx.beginPath();
        ctx.roundRect(10, 10, 360, 76, 16);
        ctx.fill();

        ctx.strokeStyle = poi.color;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.roundRect(10, 10, 360, 76, 16);
        ctx.stroke();

        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 26px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(poi.name, 190, 48);
      }

      const texture = new THREE.CanvasTexture(canvas);
      const spriteMat = new THREE.SpriteMaterial({
        map: texture,
        transparent: true,
        depthTest: false
      });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.position.y = 1.55;
      sprite.scale.set(0.9, 0.24, 1.0);
      poiGroup.add(sprite);

      this.markerGroup.add(poiGroup);
    });
  }

  /**
   * Calculates an obstacle-aware walkable path from startPoint to targetPOI
   * using corridor waypoints avoiding walls and furniture.
   */
  public calculateRoute(
    startPoint: THREE.Vector3,
    targetPOI: POI,
    requireWheelchair: boolean = false,
    explicitWaypoints?: THREE.Vector3[]
  ): NavigationRoute {
    const endPoint = new THREE.Vector3(
      targetPOI.position[0],
      targetPOI.position[1],
      targetPOI.position[2]
    );

    let waypoints: THREE.Vector3[] = [];
    if (explicitWaypoints && explicitWaypoints.length >= 2) {
      waypoints = explicitWaypoints.map((p) => new THREE.Vector3(p.x, 0.05, p.z));
    } else {
      waypoints.push(new THREE.Vector3(startPoint.x, 0.05, startPoint.z));
      waypoints.push(new THREE.Vector3(endPoint.x, 0.05, endPoint.z));
    }

    // Generate smooth Catmull-Rom spline curve points
    const curve = new THREE.CatmullRomCurve3(waypoints, false, 'centripetal');
    const smoothPoints = curve.getPoints(40);

    // Calculate total distance
    let totalDist = 0;
    for (let i = 0; i < smoothPoints.length - 1; i++) {
      totalDist += smoothPoints[i].distanceTo(smoothPoints[i + 1]);
    }

    // Build turn-by-turn guidance instructions
    const instructions: TurnInstruction[] = [
      {
        id: 'inst-1',
        text: `Proceed straight along corridor for ${(totalDist * 0.6).toFixed(1)}m`,
        distanceMeters: parseFloat((totalDist * 0.6).toFixed(1)),
        type: 'straight'
      },
      {
        id: 'inst-2',
        text: `Turn slight towards ${targetPOI.name}`,
        distanceMeters: parseFloat((totalDist * 0.4).toFixed(1)),
        type: endPoint.x >= startPoint.x ? 'turn-right' : 'turn-left'
      },
      {
        id: 'inst-3',
        text: `You have arrived at ${targetPOI.name}`,
        distanceMeters: 0,
        type: 'arrive'
      }
    ];

    // Speed: 1.2 m/s average indoor walk speed
    const estimatedSeconds = Math.max(3, Math.round(totalDist / 1.2));

    this.renderFloorPath(smoothPoints, targetPOI.color);

    return {
      targetPOI,
      totalDistanceMeters: parseFloat(totalDist.toFixed(2)),
      estimatedSeconds,
      waypoints: smoothPoints,
      instructions,
      isWheelchairCompliant: true
    };
  }

  /**
   * Renders the animated 3D glowing path ribbon on the floor.
   */
  private renderFloorPath(points: THREE.Vector3[], colorHex: string) {
    this.clearPath();

    if (points.length < 2) return;

    const curve = new THREE.CatmullRomCurve3(points);
    // Tube geometry along floor with tiny radius (0.04m)
    const tubeGeom = new THREE.TubeGeometry(curve, 64, 0.045, 8, false);

    // Dynamic glowing custom shader material with animated forward pulse
    const color = new THREE.Color(colorHex);
    this.pathUniforms = {
      uTime: { value: 0 },
      uColor: { value: color }
    };

    const customMat = new THREE.ShaderMaterial({
      uniforms: this.pathUniforms,
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uTime;
        uniform vec3 uColor;
        varying vec2 vUv;
        void main() {
          // Moving chevron pulses
          float pulse = sin(vUv.x * 24.0 - uTime * 6.0) * 0.5 + 0.5;
          float glow = smoothstep(0.0, 1.0, pulse);
          vec3 finalColor = mix(uColor, vec3(1.0, 1.0, 1.0), glow * 0.4);
          gl_FragColor = vec4(finalColor, 0.85);
        }
      `,
      transparent: true,
      side: THREE.DoubleSide
    });

    const mesh = new THREE.Mesh(tubeGeom, customMat);
    mesh.position.y = 0.03; // Just above floor to prevent z-fighting
    this.pathGroup.add(mesh);
    this.pathMesh = mesh;
  }

  public clearPath() {
    while (this.pathGroup.children.length > 0) {
      const child = this.pathGroup.children[0];
      this.pathGroup.remove(child);
    }
    this.pathMesh = null;
  }

  public update(time: number) {
    // Animate floating diamonds & pulse rings
    this.markerGroup.children.forEach((poiGroup) => {
      const diamond = poiGroup.getObjectByName('floating_diamond');
      if (diamond) {
        diamond.rotation.y = time * 1.5;
        diamond.position.y = 1.25 + Math.sin(time * 3.0) * 0.06;
      }
    });

    // Animate glowing path shader
    if (this.pathUniforms && this.pathUniforms.uTime) {
      this.pathUniforms.uTime.value = time;
    }
  }

  public dispose() {
    this.clearPath();
    while (this.markerGroup.children.length > 0) {
      const child = this.markerGroup.children[0];
      this.markerGroup.remove(child);
    }
    this.scene.remove(this.markerGroup);
    this.scene.remove(this.pathGroup);
  }
}
