import SwiftUI

/// High-fidelity 2D live provisional floorplan visualizer with observed walls, estimated boundaries, and corners
public struct LiveFloorplanView: View {
    public let floorplanMap: LiveFloorplanMap
    public let isExpanded: Bool
    
    public init(floorplanMap: LiveFloorplanMap, isExpanded: Bool = false) {
        self.floorplanMap = floorplanMap
        self.isExpanded = isExpanded
    }
    
    public var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.black.opacity(0.88))
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.white.opacity(0.18), lineWidth: 1.2)
                )
            
            GeometryReader { geo in
                let center = CGPoint(x: geo.size.width / 2.0, y: geo.size.height / 2.0)
                let scale: CGFloat = isExpanded ? 36.0 : 20.0 // pixels per meter
                
                // 1. Grid Lines (0.5 meter minor grid, 1 meter major grid)
                Path { path in
                    let step = scale
                    let w = geo.size.width
                    let h = geo.size.height
                    
                    var x = center.x
                    while x < w { path.move(to: CGPoint(x: x, y: 0)); path.addLine(to: CGPoint(x: x, y: h)); x += step }
                    x = center.x - step
                    while x > 0 { path.move(to: CGPoint(x: x, y: 0)); path.addLine(to: CGPoint(x: x, y: h)); x -= step }
                    
                    var y = center.y
                    while y < h { path.move(to: CGPoint(x: 0, y: y)); path.addLine(to: CGPoint(x: w, y: y)); y += step }
                    y = center.y - step
                    while y > 0 { path.move(to: CGPoint(x: 0, y: y)); path.addLine(to: CGPoint(x: w, y: y)); y -= step }
                }
                .stroke(Color.white.opacity(0.07), lineWidth: 0.5)
                
                // 2. Estimated / Provisional Walls (dashed cyan)
                ForEach(floorplanMap.estimatedWalls) { wall in
                    Path { path in
                        path.move(to: CGPoint(x: center.x + CGFloat(wall.start.x) * scale, y: center.y - CGFloat(wall.start.z) * scale))
                        path.addLine(to: CGPoint(x: center.x + CGFloat(wall.end.x) * scale, y: center.y - CGFloat(wall.end.z) * scale))
                    }
                    .stroke(Color.cyan.opacity(0.45), style: StrokeStyle(lineWidth: 1.5, dash: [4, 4]))
                }
                
                // 3. Observed Stable Walls (solid gold/amber)
                ForEach(floorplanMap.observedWalls) { wall in
                    Path { path in
                        path.move(to: CGPoint(x: center.x + CGFloat(wall.start.x) * scale, y: center.y - CGFloat(wall.start.z) * scale))
                        path.addLine(to: CGPoint(x: center.x + CGFloat(wall.end.x) * scale, y: center.y - CGFloat(wall.end.z) * scale))
                    }
                    .stroke(
                        LinearGradient(
                            colors: [Color.yellow, Color.orange],
                            startPoint: .leading,
                            endPoint: .trailing
                        ),
                        style: StrokeStyle(lineWidth: 3.5, lineCap: .round)
                    )
                    .shadow(color: Color.yellow.opacity(0.4), radius: 2)
                }
                
                // 4. Stable Boundary Point Cloud (for fine texture)
                ForEach(Array(floorplanMap.boundaryPoints.enumerated()), id: \.offset) { _, pt in
                    Circle()
                        .fill(Color.orange.opacity(0.75))
                        .frame(width: 3, height: 3)
                        .position(
                            x: center.x + CGFloat(pt.x) * scale,
                            y: center.y - CGFloat(pt.z) * scale
                        )
                }
                
                // 5. Room Corners
                ForEach(floorplanMap.corners) { corner in
                    ZStack {
                        Circle()
                            .fill(corner.isDirectlyObserved ? Color.green : Color.orange)
                            .frame(width: 6, height: 6)
                        
                        if isExpanded {
                            Text("\(Int(corner.angleDegrees))°")
                                .font(.system(size: 8, weight: .bold, design: .monospaced))
                                .foregroundColor(.white)
                                .offset(x: 10, y: -8)
                        }
                    }
                    .position(
                        x: center.x + CGFloat(corner.position.x) * scale,
                        y: center.y - CGFloat(corner.position.z) * scale
                    )
                }
                
                // 5b. Tracked Furniture Footprints (2D Plan View)
                ForEach(floorplanMap.furnitureObjects) { item in
                    let w = CGFloat(max(0.4, item.dimensions.width)) * scale
                    let d = CGFloat(max(0.4, item.dimensions.depth)) * scale
                    let pos = CGPoint(
                        x: center.x + CGFloat(item.position3D.x) * scale,
                        y: center.y - CGFloat(item.position3D.z) * scale
                    )
                    
                    ZStack {
                        RoundedRectangle(cornerRadius: 3)
                            .stroke(Color.teal.opacity(0.85), lineWidth: 1.5)
                            .background(RoundedRectangle(cornerRadius: 3).fill(Color.teal.opacity(0.2)))
                            .frame(width: w, height: d)
                        
                        if isExpanded {
                            Text(item.category.displayName)
                                .font(.system(size: 8, weight: .bold))
                                .foregroundColor(.white)
                        }
                    }
                    .position(pos)
                }
                
                // 6. Camera Motion Trail (cyan line)
                if floorplanMap.cameraTrail.count > 1 {
                    Path { path in
                        for (idx, pos) in floorplanMap.cameraTrail.enumerated() {
                            let p = CGPoint(
                                x: center.x + CGFloat(pos.x) * scale,
                                y: center.y - CGFloat(pos.z) * scale
                            )
                            if idx == 0 { path.move(to: p) } else { path.addLine(to: p) }
                        }
                    }
                    .stroke(Color.cyan.opacity(0.85), lineWidth: 1.8)
                }
                
                // 7. Current Camera Position & Heading Frustum
                if let current = floorplanMap.cameraTrail.last {
                    let camPos = CGPoint(
                        x: center.x + CGFloat(current.x) * scale,
                        y: center.y - CGFloat(current.z) * scale
                    )
                    
                    FrustumConeShape(headingDeg: floorplanMap.currentCameraHeadingDeg)
                        .fill(
                            LinearGradient(
                                colors: [Color.yellow.opacity(0.45), Color.clear],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                        .frame(width: 44, height: 44)
                        .position(camPos)
                    
                    Circle()
                        .fill(Color.yellow)
                        .frame(width: 8, height: 8)
                        .overlay(Circle().stroke(Color.white, lineWidth: 1.5))
                        .position(camPos)
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: 16))
            
            // Header Stats Badge
            VStack {
                HStack {
                    HStack(spacing: 4) {
                        Circle()
                            .fill(floorplanMap.coveragePercentage >= 75.0 ? Color.green : Color.orange)
                            .frame(width: 6, height: 6)
                        Text("\(Int(floorplanMap.coveragePercentage))% Coverage")
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .foregroundColor(.white)
                    }
                    .padding(.horizontal, 7)
                    .padding(.vertical, 3.5)
                    .background(Color.black.opacity(0.65))
                    .cornerRadius(6)
                    
                    Spacer()
                    
                    if !floorplanMap.observedWalls.isEmpty {
                        Text("\(floorplanMap.observedWalls.count) Walls • \(floorplanMap.corners.count) Corners")
                            .font(.system(size: 9, weight: .semibold, design: .monospaced))
                            .foregroundColor(.white.opacity(0.8))
                            .padding(.horizontal, 6)
                            .padding(.vertical, 3.5)
                            .background(Color.black.opacity(0.65))
                            .cornerRadius(6)
                    }
                }
                .padding(8)
                Spacer()
            }
        }
    }
}

