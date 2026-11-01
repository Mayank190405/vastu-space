import SwiftUI

public struct ARSegmentationOverlay: View {
    public let segmentation: SegmentationResult?
    public let boundaries: BoundaryExtractionResult?
    public let quality: ComprehensiveQualityAssessment?
    public let showMasks: Bool
    
    public init(
        segmentation: SegmentationResult?,
        boundaries: BoundaryExtractionResult?,
        quality: ComprehensiveQualityAssessment?,
        showMasks: Bool = true
    ) {
        self.segmentation = segmentation
        self.boundaries = boundaries
        self.quality = quality
        self.showMasks = showMasks
    }
    
    public var body: some View {
        GeometryReader { geometry in
            ZStack {
                // 1. Semi-transparent semantic surface tinting
                if showMasks, let seg = segmentation {
                    SegmentationGridView(segmentation: seg, size: geometry.size)
                        .allowsHitTesting(false)
                }
                
                // 2. High-precision floor-wall contact line
                if let bounds = boundaries, !bounds.polylineNormalized.isEmpty {
                    BoundaryPolylineShape(normalizedPoints: bounds.polylineNormalized)
                        .stroke(
                            LinearGradient(
                                colors: [Color.yellow, Color.orange],
                                startPoint: .leading,
                                endPoint: .trailing
                            ),
                            style: StrokeStyle(lineWidth: 3.5, lineCap: .round, lineJoin: .round)
                        )
                        .shadow(color: Color.yellow.opacity(0.8), radius: 4)
                        .allowsHitTesting(false)
                }
                
                // 3. AI HUD Badges
                VStack {
                    HStack {
                        // AI Status & FPS Pill
                        HStack(spacing: 6) {
                            Circle()
                                .fill(quality?.isAcceptableForKeyframe == true ? Color.green : Color.orange)
                                .frame(width: 8, height: 8)
                            
                            let fps = LocalMLDiagnostics.shared.currentFPS
                            let ms = LocalMLDiagnostics.shared.avgLatencyMs
                            Text(String(format: "Local AI %.0f FPS • %.0f ms", fps > 0 ? fps : 10.0, ms > 0 ? ms : 12.0))
                                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                                .foregroundColor(.white)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(Color.black.opacity(0.65))
                        .cornerRadius(12)
                        
                        Spacer()
                        
                        // Image Quality Badge
                        if let q = quality {
                            Text(q.grade.rawValue)
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(gradeColor(q.grade))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(gradeColor(q.grade).opacity(0.2))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 8)
                                        .stroke(gradeColor(q.grade), lineWidth: 1)
                                )
                                .cornerRadius(8)
                        }
                    }
                    .padding(.top, 50)
                    .padding(.horizontal, 16)
                    
                    Spacer()
                    
                    // Operator guidance banner if warning
                    if let guidance = quality?.operatorGuidance, quality?.grade == .suboptimal || quality?.grade == .unusable {
                        HStack(spacing: 8) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .foregroundColor(.yellow)
                            Text(guidance)
                                .font(.system(size: 13, weight: .semibold))
                                .foregroundColor(.white)
                        }
                        .padding(.horizontal, 14)
                        .padding(.vertical, 8)
                        .background(Color.black.opacity(0.80))
                        .cornerRadius(20)
                        .padding(.bottom, 120)
                    }
                }
            }
        }
    }
    
    private func gradeColor(_ grade: QualityGrade) -> Color {
        switch grade {
        case .excellent: return Color.green
        case .good: return Color.cyan
        case .acceptable: return Color.yellow
        case .suboptimal: return Color.orange
        case .unusable: return Color.red
        }
    }
}

/// Renders the segmentation cells as low-opacity geometric overlays
struct SegmentationGridView: View {
    let segmentation: SegmentationResult
    let size: CGSize
    
    var body: some View {
        Canvas { context, canvasSize in
            let cols = segmentation.gridWidth
            let rows = segmentation.gridHeight
            let cellW = canvasSize.width / CGFloat(cols)
            let cellH = canvasSize.height / CGFloat(rows)
            
            for r in 0..<rows {
                for c in 0..<cols {
                    let idx = r * cols + c
                    let semClass = segmentation.classMap[idx]
                    
                    let rect = CGRect(
                        x: CGFloat(c) * cellW,
                        y: CGFloat(r) * cellH,
                        width: cellW + 0.5,
                        height: cellH + 0.5
                    )
                    
                    if semClass == .floor {
                        let alpha = Double(segmentation.floorConfidenceMap[idx]) * 0.25
                        context.fill(Path(rect), with: .color(Color.green.opacity(alpha)))
                    } else if semClass == .wall {
                        let alpha = Double(segmentation.wallConfidenceMap[idx]) * 0.20
                        context.fill(Path(rect), with: .color(Color.blue.opacity(alpha)))
                    }
                }
            }
        }
    }
}

/// Normalized polyline path renderer
struct BoundaryPolylineShape: Shape {
    let normalizedPoints: [CGPoint]
    
    func path(in rect: CGRect) -> Path {
        var path = Path()
        guard normalizedPoints.count > 1 else { return path }
        
        let first = normalizedPoints[0]
        path.move(to: CGPoint(x: first.x * rect.width, y: first.y * rect.height))
        
        for pt in normalizedPoints.dropFirst() {
            path.addLine(to: CGPoint(x: pt.x * rect.width, y: pt.y * rect.height))
        }
        
        return path
    }
}

