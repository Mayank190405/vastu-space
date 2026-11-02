import SwiftUI

public struct ScanningHUD: View {
    public let instruction: GuidanceInstruction
    public let parallax: ParallaxMetric
    public let qualityAudit: ComprehensiveCaptureAudit
    
    public init(
        instruction: GuidanceInstruction,
        parallax: ParallaxMetric,
        qualityAudit: ComprehensiveCaptureAudit
    ) {
        self.instruction = instruction
        self.parallax = parallax
        self.qualityAudit = qualityAudit
    }
    
    public var body: some View {
        VStack(spacing: 10) {
            // 1. Guidance Toast with Directional Cue
            HStack(spacing: 10) {
                cueIcon(instruction.directionalCue)
                    .font(.system(size: 15, weight: .bold))
                    .foregroundColor(severityColor(instruction.severity))
                
                Text(instruction.text)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.white)
                    .multilineTextAlignment(.leading)
                
                Spacer()
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(Color.black.opacity(0.82))
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(severityColor(instruction.severity).opacity(0.6), lineWidth: 1.2)
            )
            .cornerRadius(14)
            .shadow(color: Color.black.opacity(0.3), radius: 6)
            
            // 2. Parallax Baseline & Quality Meter Ribbon
            HStack(spacing: 8) {
                // Baseline Progress
                HStack(spacing: 5) {
                    Image(systemName: "figure.walk")
                        .font(.system(size: 11))
                        .foregroundColor(parallax.isSufficient ? .green : .orange)
                    Text(String(format: "Baseline: %.2fm", parallax.translationBaselineM))
                        .font(.system(size: 11, weight: .bold, design: .monospaced))
                        .foregroundColor(.white)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.black.opacity(0.65))
                .cornerRadius(8)
                
                // Rotational Warning if detected
                if parallax.isRotationOnly {
                    HStack(spacing: 4) {
                        Image(systemName: "exclamationmark.arrow.triangle.2.circlepath")
                            .font(.system(size: 11))
                            .foregroundColor(.yellow)
                        Text("ROTATION ONLY")
                            .font(.system(size: 10, weight: .heavy))
                            .foregroundColor(.yellow)
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.yellow.opacity(0.2))
                    .cornerRadius(8)
                }
                
                Spacer()
                
                // Quality Score Pill
                HStack(spacing: 5) {
                    Text("Quality:")
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.7))
                    Text("\(Int(qualityAudit.overallScore))%")
                        .font(.system(size: 11, weight: .heavy, design: .monospaced))
                        .foregroundColor(qualityColor(qualityAudit.overallScore))
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.black.opacity(0.65))
                .cornerRadius(8)
            }
        }
        .padding(.horizontal, 16)
    }
    
    @ViewBuilder
    private func cueIcon(_ cue: DirectionalCue) -> some View {
        switch cue {
        case .forward:
            Image(systemName: "arrow.up.circle.fill")
        case .left:
            Image(systemName: "arrow.left.circle.fill")
        case .right:
            Image(systemName: "arrow.right.circle.fill")
        case .stepSideways:
            Image(systemName: "arrow.left.and.right.circle.fill")
        case .tiltDown:
            Image(systemName: "arrow.down.to.line.circle.fill")
        case .tiltUp:
            Image(systemName: "arrow.up.to.line.circle.fill")
        case .steady:
            Image(systemName: "hand.raised.fill")
        case .none:
            Image(systemName: "checkmark.circle.fill")
        }
    }
    
    private func severityColor(_ severity: GuidanceSeverity) -> Color {
        switch severity {
        case .alert: return Color.red
        case .warning: return Color.orange
        case .info: return Color.cyan
        case .success: return Color.green
        }
    }
    
    private func qualityColor(_ score: Double) -> Color {
        if score >= 75.0 { return Color.green }
        if score >= 55.0 { return Color.yellow }
        return Color.orange
    }
}

