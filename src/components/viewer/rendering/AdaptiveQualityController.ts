import * as THREE from 'three';

export interface QualityProfile {
  tier: 'DESKTOP_ULTRA' | 'DESKTOP_BALANCED' | 'MOBILE_OPTIMIZED';
  targetFPS: number;
  pixelRatio: number;
  shadowMapSize: number;
  pointCloudDecimation: number;
  antialias: boolean;
}

export class AdaptiveQualityController {
  private renderer: THREE.WebGLRenderer;
  private frameCount: number = 0;
  private lastTime: number = performance.now();
  public currentFPS: number = 60;
  public profile: QualityProfile;

  constructor(renderer: THREE.WebGLRenderer, isMobile: boolean = false) {
    this.renderer = renderer;

    if (isMobile) {
      this.profile = {
        tier: 'MOBILE_OPTIMIZED',
        targetFPS: 30,
        pixelRatio: 1.0,
        shadowMapSize: 1024,
        pointCloudDecimation: 2,
        antialias: false
      };
    } else {
      this.profile = {
        tier: 'DESKTOP_ULTRA',
        targetFPS: 60,
        pixelRatio: Math.min(window.devicePixelRatio, 2.0),
        shadowMapSize: 2048,
        pointCloudDecimation: 1,
        antialias: true
      };
    }

    this.applyProfile();
  }

  public updateFrame(): number {
    this.frameCount++;
    const now = performance.now();
    const elapsed = now - this.lastTime;

    if (elapsed >= 1000) {
      this.currentFPS = Math.round((this.frameCount * 1000) / elapsed);
      this.frameCount = 0;
      this.lastTime = now;
      this.evaluateDynamicAdjustment();
    }
    return this.currentFPS;
  }

  private evaluateDynamicAdjustment() {
    // If FPS drops below 80% of target, drop down tier to preserve smooth responsiveness
    if (this.currentFPS < this.profile.targetFPS * 0.75) {
      if (this.profile.tier === 'DESKTOP_ULTRA') {
        this.profile.tier = 'DESKTOP_BALANCED';
        this.profile.pixelRatio = 1.25;
        this.profile.shadowMapSize = 1024;
        this.applyProfile();
      } else if (this.profile.tier === 'DESKTOP_BALANCED') {
        this.profile.tier = 'MOBILE_OPTIMIZED';
        this.profile.pixelRatio = 1.0;
        this.profile.shadowMapSize = 512;
        this.applyProfile();
      }
    }
  }

  private applyProfile() {
    this.renderer.setPixelRatio(this.profile.pixelRatio);
    if (this.renderer.shadowMap.enabled) {
      this.renderer.shadowMap.type =
        this.profile.tier === 'DESKTOP_ULTRA' ? THREE.PCFSoftShadowMap : THREE.BasicShadowMap;
    }
  }
}

