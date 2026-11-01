import * as THREE from 'three';

export class IsometricViewOptimizer {
  /**
   * Generates billboard text canvas sprite for room labels in isometric mode.
   */
  public static createRoomLabelSprite(roomName: string, areaSqm: number): THREE.Sprite {
    const canvas = document.createElement('canvas');
    canvas.width = 384;
    canvas.height = 128;
    const ctx = canvas.getContext('2d')!;

    // Rounded pill background
    ctx.fillStyle = 'rgba(15, 23, 42, 0.88)'; // Slate-900 with alpha
    ctx.strokeStyle = '#C5A059';
    ctx.lineWidth = 4;
    this.roundRect(ctx, 8, 8, 368, 112, 24);
    ctx.fill();
    ctx.stroke();

    // Text: Room Name
    ctx.fillStyle = '#FFFFFF';
    ctx.font = 'bold 36px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(roomName, 192, 56);

    // Text: Area
    ctx.fillStyle = '#C5A059';
    ctx.font = 'bold 24px Inter, sans-serif';
    ctx.fillText(`${areaSqm.toFixed(1)} m²`, 192, 94);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.scale.set(3.2, 1.05, 1.0);
    return sprite;
  }

  private static roundRect(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    w: number,
    h: number,
    r: number
  ) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }
}

