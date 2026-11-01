import * as THREE from 'three';

export class RoomVisibilityManager {
  private roomMeshes: Map<string, THREE.Object3D> = new Map();
  private ceilingMeshes: THREE.Object3D[] = [];
  private isCeilingVisible: boolean = false;
  private currentMode: 'walk' | 'isometric' = 'walk';
  private adjacentRoomMap: Map<string, Set<string>> = new Map();

  public registerRoomMesh(roomId: string, mesh: THREE.Object3D) {
    this.roomMeshes.set(roomId, mesh);
  }

  public registerCeilingMesh(mesh: THREE.Object3D) {
    this.ceilingMeshes.push(mesh);
    mesh.visible = this.isCeilingVisible;
  }

  public setAdjacentRooms(roomId: string, neighbors: string[]) {
    this.adjacentRoomMap.set(roomId, new Set(neighbors));
  }

  public setMode(mode: 'walk' | 'isometric') {
    this.currentMode = mode;
    this.updateVisibility();
  }

  public toggleCeilingVisibility(): boolean {
    this.isCeilingVisible = !this.isCeilingVisible;
    for (const ceiling of this.ceilingMeshes) {
      ceiling.visible = this.isCeilingVisible;
    }
    return this.isCeilingVisible;
  }

  public updateActiveRoom(activeRoomId: string) {
    if (this.currentMode === 'isometric') {
      // In isometric mode, display all rooms
      for (const mesh of this.roomMeshes.values()) {
        mesh.visible = true;
      }
      return;
    }

    // In walk mode: keep active room and direct adjacent rooms visible
    const neighbors = this.adjacentRoomMap.get(activeRoomId) || new Set<string>();
    for (const [rid, mesh] of this.roomMeshes.entries()) {
      mesh.visible = (rid === activeRoomId || neighbors.has(rid));
    }
  }

  private updateVisibility() {
    if (this.currentMode === 'isometric') {
      for (const mesh of this.roomMeshes.values()) {
        mesh.visible = true;
      }
      for (const c of this.ceilingMeshes) {
        c.visible = this.isCeilingVisible;
      }
    } else {
      // Walk mode: ceiling can be visible if requested
      for (const c of this.ceilingMeshes) {
        c.visible = true;
      }
    }
  }
}

