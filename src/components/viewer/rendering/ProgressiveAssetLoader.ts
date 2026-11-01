export interface StreamingStage {
  stageName: string;
  bytesLoaded: number;
  totalBytes: number;
  isComplete: boolean;
}

export class ProgressiveAssetLoader {
  private stages: Map<string, StreamingStage> = new Map();
  private onProgressCallback?: (overallPercent: number, statusText: string) => void;

  constructor(onProgress?: (overallPercent: number, statusText: string) => void) {
    this.onProgressCallback = onProgress;
  }

  public registerStage(name: string, totalBytesEstimate: number) {
    this.stages.set(name, {
      stageName: name,
      bytesLoaded: 0,
      totalBytes: totalBytesEstimate,
      isComplete: false
    });
    this.emitProgress();
  }

  public updateStage(name: string, loaded: number, total?: number) {
    const stage = this.stages.get(name);
    if (!stage) return;
    stage.bytesLoaded = loaded;
    if (total) stage.totalBytes = total;
    if (stage.bytesLoaded >= stage.totalBytes) {
      stage.isComplete = true;
    }
    this.emitProgress();
  }

  public completeStage(name: string) {
    const stage = this.stages.get(name);
    if (!stage) return;
    stage.bytesLoaded = stage.totalBytes;
    stage.isComplete = true;
    this.emitProgress();
  }

  private emitProgress() {
    let totalLoaded = 0;
    let totalExpected = 0;
    let activeStageName = 'Initializing';

    for (const s of this.stages.values()) {
      totalLoaded += s.bytesLoaded;
      totalExpected += s.totalBytes;
      if (!s.isComplete && activeStageName === 'Initializing') {
        activeStageName = s.stageName;
      }
    }

    const pct = totalExpected > 0 ? Math.min(100, Math.round((totalLoaded / totalExpected) * 100)) : 100;
    this.onProgressCallback?.(pct, activeStageName);
  }
}

