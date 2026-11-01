import SwiftUI

public struct MiniMapFloorplanView: View {
    public let floorplanMap: LiveFloorplanMap
    
    public init(floorplanMap: LiveFloorplanMap) {
        self.floorplanMap = floorplanMap
    }
    
    public var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 14)
                .fill(Color.black.opacity(0.85))
                .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.white.opacity(0.2), lineWidth: 1))
            
            GeometryReader { geo in
                let center = CGPoint(x: geo.size.width / 2.0, y: geo.size.height / 2.0)
                let scale: CGFloat = 18.0 // 18 pixels per meter
                
                // 1. Grid Lines
                Path { path in
                    for x in stride(from: 0, to: geo.size.width, by: 20) {
                        path.move(to: CGPoint(x: x, y: 0))
                        path.addLine(to: CGPoint(x: x, y: geo.size.height))
                    }
                    for y in stride(from: 0, to: geo.size.height, by: 20) {
                        path.move(to: CGPoint(x: 0, y: y))
                        path.addLine(to: CGPoint(x: geo.size.width, y: y))
                    }
                }
                .stroke(Color.white.opacity(0.08), lineWidth: 0.5)
                
                // 2. Accumulated Boundary Points
                ForEach(Array(floorplanMap.boundaryPoints.enumerated()), id: \.offset) { _, pt in
                    Circle()
                        .fill(VastuColors.brandBronze.opacity(0.8))
                        .frame(width: 3.5, height: 3.5)
                        .position(
                            x: center.x + CGFloat(pt.x) * scale,
                            y: center.y - CGFloat(pt.z) * scale
                        )
                }
                
                // 3. Camera Movement Trail
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
                    .stroke(Color.cyan.opacity(0.9), lineWidth: 2)
                }
                
                // 4. Current Camera Position & Heading Frustum
                if let current = floorplanMap.cameraTrail.last {
                    let camPos = CGPoint(
                        x: center.x + CGFloat(current.x) * scale,
                        y: center.y - CGFloat(current.z) * scale
                    )
                    
                    // Frustum Cone
                    FrustumConeShape(headingDeg: floorplanMap.currentCameraHeadingDeg)
                        .fill(
                            LinearGradient(
                                colors: [Color.yellow.opacity(0.4), Color.clear],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                        .frame(width: 40, height: 40)
                        .position(camPos)
                    
                    // Camera Dot
                    Circle()
                        .fill(Color.yellow)
                        .frame(width: 7, height: 7)
                        .position(camPos)
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: 14))
            
            // Coverage Badge
            VStack {
                HStack {
                    Spacer()
                    Text("\(Int(floorplanMap.coveragePercentage))% Coverage")
                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                        .foregroundColor(VastuColors.brandIvory)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 3)
                        .background(Color.black.opacity(0.6))
                        .cornerRadius(6)
                }
                .padding(6)
                Spacer()
            }
        }
        .frame(width: 140, height: 140)
    }
}

public struct FrustumConeShape: Shape {
    public let headingDeg: Double
    public init(headingDeg: Double) { self.headingDeg = headingDeg }
    public func path(in rect: CGRect) -> Path {
        var path = Path()
        let center = CGPoint(x: rect.midX, y: rect.midY)
        path.move(to: center)
        let rad = CGFloat((headingDeg - 90.0) * .pi / 180.0)
        let spread: CGFloat = 0.4
        let len: CGFloat = rect.width / 2.0
        
        path.addLine(to: CGPoint(x: center.x + cos(rad - spread) * len, y: center.y + sin(rad - spread) * len))
        path.addLine(to: CGPoint(x: center.x + cos(rad + spread) * len, y: center.y + sin(rad + spread) * len))
        path.closeSubpath()
        return path
    }
}

public struct CaptureGuidanceToast: View {
    public let text: String
    public init(text: String) { self.text = text }
    
    public var body: some View {
        HStack(spacing: 8) {
            Image(systemName: "figure.walk.motion")
                .font(.system(size: 13, weight: .bold))
                .foregroundColor(VastuColors.brandGold)
            Text(text)
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(.white)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(.black.opacity(0.85))
        .cornerRadius(20)
        .overlay(RoundedRectangle(cornerRadius: 20).stroke(VastuColors.brandBronze.opacity(0.6), lineWidth: 1))
        .shadow(color: Color.black.opacity(0.3), radius: 6, x: 0, y: 2)
    }
}

public struct TrackingStatusPill: View {
    public let state: String
    public let isWarning: Bool
    
    public init(state: String, isWarning: Bool) {
        self.state = state
        self.isWarning = isWarning
    }
    
    public var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(isWarning ? VastuColors.brandWarning : VastuColors.brandSuccess)
                .frame(width: 8, height: 8)
            Text(displayText)
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(.white)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(.ultraThinMaterial)
        .cornerRadius(16)
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.white.opacity(0.2), lineWidth: 1))
    }
    
    private var displayText: String {
        switch state {
        case "NORMAL": return "VIO Tracking: Normal"
        case "LIMITED_EXCESSIVE_MOTION": return "Fast Motion"
        case "LIMITED_INSUFFICIENT_FEATURES": return "Low Contrast"
        case "LIMITED_INITIALIZING": return "Initializing..."
        default: return "Tracking Unavailable"
        }
    }
}

