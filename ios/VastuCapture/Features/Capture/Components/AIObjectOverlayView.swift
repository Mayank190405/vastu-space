import SwiftUI

/// Real-time SwiftUI overlay view for 2D/3D detected furniture objects and optional depth heatmap
public struct AIObjectOverlayView: View {
    public let detectedObjects: [DetectedFurniture]
    public let trackedFurniture: [TrackedFurnitureObject]
    public let depthResult: DepthEstimationResult?
    public let showDepthHeatmap: Bool
    
    public init(
        detectedObjects: [DetectedFurniture],
        trackedFurniture: [TrackedFurnitureObject],
        depthResult: DepthEstimationResult? = nil,
        showDepthHeatmap: Bool = false
    ) {
        self.detectedObjects = detectedObjects
        self.trackedFurniture = trackedFurniture
        self.depthResult = depthResult
        self.showDepthHeatmap = showDepthHeatmap
    }
    
    public var body: some View {
        GeometryReader { geo in
            ZStack {
                // 1. Optional Monocular Depth Heatmap Overlay
                if showDepthHeatmap, let depth = depthResult {
                    DepthHeatmapCanvas(depth: depth, size: geo.size)
                        .opacity(0.35)
                        .allowsHitTesting(false)
                }
                
                // 2. 2D Furniture Bounding Boxes and Metadata Cards
                ForEach(detectedObjects) { obj in
                    let bb = obj.boundingBox
                    if bb.count == 4 {
                        let rect = CGRect(
                            x: bb[0] * geo.size.width,
                            y: bb[1] * geo.size.height,
                            width: bb[2] * geo.size.width,
                            height: bb[3] * geo.size.height
                        )
                        
                        // Find matching 3D track for distance and uncertainty
                        let matchingTrack = trackedFurniture.first { $0.category == obj.category }
                        
                        FurnitureBoundingBoxView(
                            object: obj,
                            rect: rect,
                            track: matchingTrack
                        )
                    }
                }
            }
        }
    }
}

/// Renders bounding box, corner anchors, and floating label badge
struct FurnitureBoundingBoxView: View {
    let object: DetectedFurniture
    let rect: CGRect
    let track: TrackedFurnitureObject?
    
    var body: some View {
        ZStack(alignment: .topLeading) {
            // Outline
            RoundedRectangle(cornerRadius: 10)
                .stroke(categoryColor(object.category), lineWidth: 2.2)
                .background(categoryColor(object.category).opacity(0.12))
                .frame(width: rect.width, height: rect.height)
                .position(x: rect.midX, y: rect.midY)
            
            // Label Badge
            HStack(spacing: 5) {
                categoryIcon(object.category)
                    .font(.system(size: 10, weight: .bold))
                
                Text(object.label)
                    .font(.system(size: 11, weight: .bold))
                
                Text("\(Int(object.confidence * 100))%")
                    .font(.system(size: 10, weight: .semibold, design: .monospaced))
                    .foregroundColor(.white.opacity(0.8))
                
                if let t = track {
                    let dist = sqrt(t.position3D.x * t.position3D.x + t.position3D.z * t.position3D.z)
                    Text(String(format: "• %.1fm ±%.1fm", dist, t.uncertaintyMeters))
                        .font(.system(size: 9, weight: .medium, design: .monospaced))
                        .foregroundColor(.yellow)
                }
            }
            .foregroundColor(.white)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(categoryColor(object.category).opacity(0.88))
            .cornerRadius(6)
            .position(x: rect.minX + 60, y: max(20, rect.minY - 14))
        }
    }
    
    private func categoryColor(_ cat: FurnitureCategory) -> Color {
        switch cat {
        case .bed: return Color.purple
        case .sofa: return Color.teal
        case .chair: return Color.blue
        case .table, .desk: return Color.orange
        case .cabinet, .wardrobe: return Color.indigo
        case .tvStand: return Color.pink
        case .door, .window: return Color.cyan
        case .unknown: return Color.gray
        }
    }
    
    @ViewBuilder
    private func categoryIcon(_ cat: FurnitureCategory) -> some View {
        switch cat {
        case .bed: Image(systemName: "bed.double.fill")
        case .sofa: Image(systemName: "sofa.fill")
        case .chair: Image(systemName: "chair.fill")
        case .table, .desk: Image(systemName: "table.furniture.fill")
        case .cabinet, .wardrobe: Image(systemName: "cabinet.fill")
        case .tvStand: Image(systemName: "tv.fill")
        case .door: Image(systemName: "door.left.hand.open")
        case .window: Image(systemName: "window.vertical.closed")
        case .unknown: Image(systemName: "cube.fill")
        }
    }
}

/// Canvas rendering normalized depth values using heat colormap
struct DepthHeatmapCanvas: View {
    let depth: DepthEstimationResult
    let size: CGSize
    
    var body: some View {
        Canvas { context, canvasSize in
            let cols = depth.width
            let rows = depth.height
            let cellW = canvasSize.width / CGFloat(cols)
            let cellH = canvasSize.height / CGFloat(rows)
            
            for r in 0..<rows {
                for c in 0..<cols {
                    let idx = r * cols + c
                    let d = depth.relativeDepthMap[idx] // 0.0 (near) to 1.0 (far)
                    
                    let rect = CGRect(
                        x: CGFloat(c) * cellW,
                        y: CGFloat(r) * cellH,
                        width: cellW + 0.5,
                        height: cellH + 0.5
                    )
                    
                    // Turbo-like colormap: purple (near) -> cyan -> yellow -> red (far)
                    let col = depthColor(d)
                    context.fill(Path(rect), with: .color(col))
                }
            }
        }
    }
    
    private func depthColor(_ val: Float) -> Color {
        let v = Double(max(0.0, min(1.0, val)))
        if v < 0.33 {
            return Color.blue.opacity(0.4)
        } else if v < 0.66 {
            return Color.green.opacity(0.4)
        } else {
            return Color.red.opacity(0.4)
        }
    }
}

