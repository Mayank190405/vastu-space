import SwiftUI
import simd

/// Interactive Top-Down 2D Spatial Coverage Map supporting Pan, Zoom, Rotation, and Region Selection (IOS-011)
public struct LiveRoomMapView: View {
    public let floorplanMap: LiveFloorplanMap
    public let availableRegions: [SpatialRegion]
    public let selectedRegionId: String?
    public let onSelectRegion: (String) -> Void
    
    @State private var scale: CGFloat = 1.0
    @State private var lastScale: CGFloat = 1.0
    @State private var offset: CGSize = .zero
    @State private var lastOffset: CGSize = .zero
    @State private var rotationAngle: Angle = .zero
    
    public init(
        floorplanMap: LiveFloorplanMap,
        availableRegions: [SpatialRegion] = [],
        selectedRegionId: String? = nil,
        onSelectRegion: @escaping (String) -> Void = { _ in }
    ) {
        self.floorplanMap = floorplanMap
        self.availableRegions = availableRegions
        self.selectedRegionId = selectedRegionId
        self.onSelectRegion = onSelectRegion
    }
    
    public var body: some View {
        GeometryReader { geo in
            let center = CGPoint(x: geo.size.width / 2.0, y: geo.size.height / 2.0)
            let baseScale = min(geo.size.width, geo.size.height) / 10.0
            
            ZStack {
                // Background canvas with grid pattern
                Color(red: 0.05, green: 0.07, blue: 0.10)
                    .overlay(gridLines(geo: geo))
                
                // Transformed Map Elements
                ZStack {
                    // 1. Incomplete / Available Spatial Regions
                    ForEach(availableRegions) { region in
                        regionOverlay(region: region, center: center, ppm: baseScale)
                            .onTapGesture {
                                onSelectRegion(region.id)
                            }
                    }
                    
                    // 2. Mapped Wall Segments
                    ForEach(floorplanMap.observedWalls) { wall in
                        Path { path in
                            let start = toScreen(pt: wall.start, center: center, ppm: baseScale)
                            let end = toScreen(pt: wall.end, center: center, ppm: baseScale)
                            path.move(to: start)
                            path.addLine(to: end)
                        }
                        .stroke(
                            wall.confidence > 0.7 ? Color(red: 0.87, green: 0.72, blue: 0.45) : Color(red: 0.58, green: 0.64, blue: 0.72),
                            style: StrokeStyle(lineWidth: 3.5, lineCap: .round)
                        )
                    }
                    
                    // 3. Mapped Architectural Corners
                    ForEach(floorplanMap.corners) { corner in
                        let pt = toScreen(pt: corner.position, center: center, ppm: baseScale)
                        Circle()
                            .fill(corner.isDirectlyObserved ? Color.green : Color.orange)
                            .frame(width: 8, height: 8)
                            .position(pt)
                    }
                    
                    // 4. Mapped Furniture Footprints
                    ForEach(floorplanMap.furnitureObjects) { item in
                        furnitureFootprint(item: item, center: center, ppm: baseScale)
                    }
                    
                    // 5. Camera Trajectory Path
                    if floorplanMap.cameraTrail.count > 1 {
                        Path { path in
                            let pts = floorplanMap.cameraTrail.map { toScreen(pt: $0, center: center, ppm: baseScale) }
                            path.move(to: pts[0])
                            for p in pts.dropFirst() {
                                path.addLine(to: p)
                            }
                        }
                        .stroke(Color.cyan.opacity(0.6), style: StrokeStyle(lineWidth: 2, dash: [4, 3]))
                    }
                    
                    // 6. Current Camera Pose & Heading Cone
                    let camPt = toScreen(pt: floorplanMap.cameraTrail.last ?? Point2D(x: 0, z: 0), center: center, ppm: baseScale)
                    cameraFrustumView(at: camPt, headingDeg: floorplanMap.currentCameraHeadingDeg)
                }
                .scaleEffect(scale)
                .offset(offset)
                .rotationEffect(rotationAngle)
                
                // Top-left map legend and controls
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 8) {
                        Image(systemName: "map.fill")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(Color(red: 0.87, green: 0.72, blue: 0.45))
                        Text("LIVE ROOM MAP")
                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                            .foregroundColor(.white)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Color.black.opacity(0.65))
                    .cornerRadius(8)
                    
                    Spacer()
                    
                    // Map controls and legend
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            legendPill(color: .green, label: "Complete (≥90%)")
                            legendPill(color: .orange, label: "Incomplete")
                            legendPill(color: .cyan, label: "Selected for Rescan")
                        }
                        .padding(8)
                        .background(Color.black.opacity(0.65))
                        .cornerRadius(8)
                        
                        Spacer()
                        
                        Button(action: resetMapTransform) {
                            Image(systemName: "arrow.counterclockwise")
                                .font(.system(size: 13, weight: .semibold))
                                .foregroundColor(.white)
                                .frame(width: 32, height: 32)
                                .background(Color.black.opacity(0.65))
                                .clipShape(Circle())
                        }
                    }
                }
                .padding(12)
            }
            .gesture(
                SimultaneousGesture(
                    MagnificationGesture()
                        .onChanged { val in
                            scale = max(0.5, min(3.5, lastScale * val))
                        }
                        .onEnded { _ in
                            lastScale = scale
                        },
                    DragGesture()
                        .onChanged { val in
                            offset = CGSize(
                                width: lastOffset.width + val.translation.width,
                                height: lastOffset.height + val.translation.height
                            )
                        }
                        .onEnded { _ in
                            lastOffset = offset
                        }
                )
            )
        }
    }
    
    private func resetMapTransform() {
        withAnimation(.spring()) {
            scale = 1.0
            lastScale = 1.0
            offset = .zero
            lastOffset = .zero
            rotationAngle = .zero
        }
    }
    
    private func toScreen(pt: Point2D, center: CGPoint, ppm: CGFloat) -> CGPoint {
        CGPoint(x: center.x + CGFloat(pt.x) * ppm, y: center.y + CGFloat(pt.z) * ppm)
    }
    
    private func regionOverlay(region: SpatialRegion, center: CGPoint, ppm: CGFloat) -> some View {
        let isSelected = (region.id == selectedRegionId) || region.isSelectedForRescan
        let strokeColor: Color = isSelected ? Color.cyan : (region.isComplete ? Color.green.opacity(0.7) : Color.orange.opacity(0.8))
        
        return ZStack {
            if region.polygonPoints.count >= 2 {
                Path { path in
                    let pts = region.polygonPoints.map { toScreen(pt: $0, center: center, ppm: ppm) }
                    path.move(to: pts[0])
                    for p in pts.dropFirst() {
                        path.addLine(to: p)
                    }
                }
                .stroke(strokeColor, style: StrokeStyle(lineWidth: isSelected ? 3.0 : 2.0, dash: isSelected ? [6, 4] : []))
                
                // Region badge label at midpoint
                if let first = region.polygonPoints.first, let last = region.polygonPoints.last {
                    let midX = (first.x + last.x) / 2.0
                    let midZ = (first.z + last.z) / 2.0
                    let midScreen = toScreen(pt: Point2D(x: midX, z: midZ), center: center, ppm: ppm)
                    
                    HStack(spacing: 4) {
                        Text("\(region.name): \(Int(region.qualityScore))%")
                            .font(.system(size: 9, weight: .bold, design: .monospaced))
                            .foregroundColor(isSelected ? .black : .white)
                    }
                    .padding(.horizontal, 6)
                    .padding(.vertical, 3)
                    .background(isSelected ? Color.cyan : (region.isComplete ? Color.green.opacity(0.8) : Color.orange.opacity(0.85)))
                    .cornerRadius(6)
                    .position(midScreen)
                }
            }
        }
    }
    
    private func furnitureFootprint(item: TrackedFurnitureObject, center: CGPoint, ppm: CGFloat) -> some View {
        let pt = toScreen(pt: Point2D(x: item.position3D.x, z: item.position3D.z), center: center, ppm: ppm)
        let w = max(24.0, CGFloat(item.dimensions.width) * ppm)
        let d = max(18.0, CGFloat(item.dimensions.depth) * ppm)
        
        return ZStack {
            RoundedRectangle(cornerRadius: 4)
                .fill(Color(red: 0.22, green: 0.28, blue: 0.36).opacity(0.85))
                .frame(width: w, height: d)
                .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.cyan.opacity(0.6), lineWidth: 1.5))
            
            Text(item.category.rawValue.prefix(4).uppercased())
                .font(.system(size: 8, weight: .bold, design: .monospaced))
                .foregroundColor(.white)
        }
        .position(pt)
    }
    
    private func cameraFrustumView(at pt: CGPoint, headingDeg: Double) -> some View {
        ZStack {
            // Field of view cone
            Path { path in
                path.move(to: .zero)
                path.addLine(to: CGPoint(x: -18, y: -36))
                path.addLine(to: CGPoint(x: 18, y: -36))
                path.closeSubpath()
            }
            .fill(
                LinearGradient(
                    colors: [Color.cyan.opacity(0.7), Color.cyan.opacity(0.0)],
                    startPoint: .bottom,
                    endPoint: .top
                )
            )
            .rotationEffect(.degrees(headingDeg))
            
            // Camera position dot
            Circle()
                .fill(Color.cyan)
                .frame(width: 10, height: 10)
                .overlay(Circle().stroke(Color.white, lineWidth: 2))
        }
        .position(pt)
    }
    
    private func gridLines(geo: GeometryProxy) -> some View {
        Path { path in
            let step: CGFloat = 24.0
            var x: CGFloat = 0
            while x < geo.size.width {
                path.move(to: CGPoint(x: x, y: 0))
                path.addLine(to: CGPoint(x: x, y: geo.size.height))
                x += step
            }
            var y: CGFloat = 0
            while y < geo.size.height {
                path.move(to: CGPoint(x: 0, y: y))
                path.addLine(to: CGPoint(x: geo.size.width, y: y))
                y += step
            }
        }
        .stroke(Color.white.opacity(0.05), lineWidth: 1)
    }
    
    private func legendPill(color: Color, label: String) -> some View {
        HStack(spacing: 5) {
            Circle().fill(color).frame(width: 6, height: 6)
            Text(label)
                .font(.system(size: 9, weight: .medium))
                .foregroundColor(.white.opacity(0.8))
        }
    }
}
