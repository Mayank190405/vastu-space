import SwiftUI

public struct VastuPreloaderView: View {
    public var targetMessage: String = "Welcome to VĀSTU Control Plane"
    public var onFinish: () -> Void
    
    @State private var statusText: String = "Securing workspace tokens..."
    @State private var progress: CGFloat = 0.15
    @State private var isRotating: Bool = false
    @State private var isPulsing: Bool = false
    
    public init(targetMessage: String = "Welcome to VĀSTU Control Plane", onFinish: @escaping () -> Void) {
        self.targetMessage = targetMessage
        self.onFinish = onFinish
    }
    
    public var body: some View {
        ZStack {
            VastuColors.brandParchment.ignoresSafeArea()
            
            VStack(spacing: 24) {
                // Rotating Compass Halo & Breathing Logo
                ZStack {
                    // Outer rotating compass halo
                    Circle()
                        .stroke(
                            AngularGradient(
                                gradient: Gradient(colors: [
                                    VastuColors.brandBronze.opacity(0.9),
                                    Color.clear,
                                    VastuColors.brandBronze.opacity(0.4),
                                    Color.clear,
                                    VastuColors.brandBronze.opacity(0.9)
                                ]),
                                center: .center
                            ),
                            lineWidth: 2
                        )
                        .frame(width: 140, height: 140)
                        .rotationEffect(.degrees(isRotating ? 360 : 0))
                        .animation(Animation.linear(duration: 4.0).repeatForever(autoreverses: false), value: isRotating)
                    
                    // Central Card with Vastu Logo
                    ZStack {
                        Circle()
                            .fill(VastuColors.brandIvory)
                            .frame(width: 104, height: 104)
                            .overlay(
                                Circle()
                                    .stroke(VastuColors.brandBronze.opacity(0.4), lineWidth: 1.5)
                            )
                            .shadow(color: VastuColors.brandBronze.opacity(0.15), radius: 8, x: 0, y: 4)
                        
                        if let imagePath = Bundle.main.path(forResource: "vastu_logo", ofType: "png"),
                           let uiImage = UIImage(contentsOfFile: imagePath) {
                            Image(uiImage: uiImage)
                                .resizable()
                                .scaledToFit()
                                .frame(width: 72, height: 72)
                        } else if let uiImage = UIImage(named: "vastu_logo") {
                            Image(uiImage: uiImage)
                                .resizable()
                                .scaledToFit()
                                .frame(width: 72, height: 72)
                        } else {
                            Text("VĀSTU")
                                .font(.system(size: 16, weight: .bold, design: .serif))
                                .foregroundColor(VastuColors.brandBronze)
                        }
                    }
                    .scaleEffect(isPulsing ? 1.05 : 0.95)
                    .animation(Animation.easeInOut(duration: 1.2).repeatForever(autoreverses: true), value: isPulsing)
                }
                
                // Brand Typography
                VStack(spacing: 4) {
                    Text("V Ā S T U")
                        .font(.system(size: 24, weight: .bold, design: .serif))
                        .tracking(6)
                        .foregroundColor(VastuColors.brandBronze)
                    
                    Text("Spatial Intelligence Platform")
                        .font(.system(size: 12, weight: .medium))
                        .tracking(1.5)
                        .foregroundColor(VastuColors.brandTextMuted)
                }
                
                Spacer().frame(height: 12)
                
                // Telemetry Progress Bar
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(VastuColors.brandBronze.opacity(0.15))
                        .frame(width: 220, height: 3)
                    
                    Capsule()
                        .fill(VastuColors.brandBronze)
                        .frame(width: 220 * progress, height: 3)
                        .animation(.easeInOut(duration: 0.4), value: progress)
                }
                
                // Dynamic Status Text
                Text(statusText)
                    .font(.system(size: 12, weight: .regular))
                    .foregroundColor(VastuColors.brandTextMuted)
                    .multilineTextAlignment(.center)
            }
            .padding(32)
        }
        .onAppear {
            isRotating = true
            isPulsing = true
            
            // Sequential telemetry
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                statusText = "Authenticating organization workspace..."
                progress = 0.40
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.9) {
                statusText = "Synchronizing digital twin coordinates..."
                progress = 0.70
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.4) {
                statusText = "Initializing spatial coordinate engine..."
                progress = 0.90
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.8) {
                statusText = targetMessage
                progress = 1.0
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.2) {
                onFinish()
            }
        }
    }
}
