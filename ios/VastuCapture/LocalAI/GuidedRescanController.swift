import Foundation
import simd

public enum RescanState: String, Codable {
    case idle = "IDLE"
    case regionSelected = "REGION_SELECTED"
    case relocalizing = "RELOCALIZING"
    case scanning = "SCANNING"
    case checkingObservations = "CHECKING_OBSERVATIONS"
    case mergedSuccess = "MERGED_SUCCESS"
    case alignmentFailed = "ALIGNMENT_FAILED"
}

public struct SpatialRegion: Identifiable, Codable {
    public let id: String
    public let name: String
    public let polygonPoints: [Point2D]
    public var coveragePct: Double
    public var qualityScore: Double
    public var isComplete: Bool
    public var isSelectedForRescan: Bool
    
    public init(
        id: String,
        name: String,
        polygonPoints: [Point2D],
        coveragePct: Double,
        qualityScore: Double,
        isComplete: Bool = false,
        isSelectedForRescan: Bool = false
    ) {
        self.id = id
        self.name = name
        self.polygonPoints = polygonPoints
        self.coveragePct = coveragePct
        self.qualityScore = qualityScore
        self.isComplete = isComplete
        self.isSelectedForRescan = isSelectedForRescan
    }
}

/// Intelligent Guided Rescan Controller managing selective rescans, relocalization, and evidence merging (IOS-012)
public final class GuidedRescanController: ObservableObject {
    public static let shared = GuidedRescanController()
    
    @Published public var state: RescanState = .idle
    @Published public var selectedRegion: SpatialRegion?
    @Published public var availableRegions: [SpatialRegion] = []
    @Published public var rescanKeyframesCollected: Int = 0
    @Published public var alignmentErrorMeters: Double = 0.0
    @Published public var statusMessage: String = "Ready for capture review or rescan"
    
    private let relocalizationMaxToleranceMeters: Double = 0.15
    
    public init() {
        populateDefaultRegions()
    }
    
    public func reset() {
        state = .idle
        selectedRegion = nil
        rescanKeyframesCollected = 0
        alignmentErrorMeters = 0.0
        statusMessage = "Ready for capture review or rescan"
        populateDefaultRegions()
    }
    
    public func populateDefaultRegions() {
        // Construct canonical room perimeter regions
        availableRegions = [
            SpatialRegion(
                id: "wall-north",
                name: "North Wall Segment",
                polygonPoints: [Point2D(x: -2.0, z: -2.0), Point2D(x: 2.0, z: -2.0)],
                coveragePct: 92.0,
                qualityScore: 94.0,
                isComplete: true
            ),
            SpatialRegion(
                id: "wall-east",
                name: "East Wall & Window",
                polygonPoints: [Point2D(x: 2.0, z: -2.0), Point2D(x: 2.0, z: 2.0)],
                coveragePct: 88.0,
                qualityScore: 89.0,
                isComplete: false
            ),
            SpatialRegion(
                id: "wall-south",
                name: "South Wall & Doorway",
                polygonPoints: [Point2D(x: 2.0, z: 2.0), Point2D(x: -2.0, z: 2.0)],
                coveragePct: 95.0,
                qualityScore: 96.0,
                isComplete: true
            ),
            SpatialRegion(
                id: "wall-west",
                name: "West Wall (Low Coverage)",
                polygonPoints: [Point2D(x: -2.0, z: 2.0), Point2D(x: -2.0, z: -2.0)],
                coveragePct: 58.0,
                qualityScore: 62.0,
                isComplete: false
            )
        ]
    }
    
    /// Step 1: Operator selects an incomplete region on the map
    public func selectRegion(id: String) {
        if !availableRegions.contains(where: { $0.id == id }) {
            let dynRegion = SpatialRegion(
                id: id,
                name: "Incomplete Sector (\(id))",
                polygonPoints: [Point2D(x: -1.5, z: 0.0), Point2D(x: -1.5, z: 2.0)],
                coveragePct: 55.0,
                qualityScore: 60.0,
                isComplete: false,
                isSelectedForRescan: true
            )
            availableRegions.append(dynRegion)
        }
        for idx in 0..<availableRegions.count {
            availableRegions[idx].isSelectedForRescan = (availableRegions[idx].id == id)
        }
        selectedRegion = availableRegions.first(where: { $0.id == id })
        if let sel = selectedRegion {
            state = .regionSelected
            statusMessage = "Selected \(sel.name). Tap 'Rescan Area' to begin guided sweep."
        }
    }
    
    /// Step 3: Operator chooses Rescan Area
    public func startRescan(onRelocalizeNeeded: () -> Bool) {
        guard let region = selectedRegion else { return }
        state = .relocalizing
        statusMessage = "Aligning camera with existing room map..."
        
        // Attempt relocalization against mapped spatial anchors
        let relocalized = onRelocalizeNeeded()
        if !relocalized {
            state = .alignmentFailed
            statusMessage = "Relocalization failed. Move phone to a previously scanned wall to regain tracking."
            return
        }
        
        state = .scanning
        rescanKeyframesCollected = 0
        statusMessage = "Scanning \(region.name) • Follow directional arrows and TTS instructions."
        
        // Announce via TTS
        TTSGuidanceController.shared.speakInstruction(GuidanceInstruction(
            text: "Move toward the highlighted region and follow the guide.",
            severity: .info,
            directionalCue: .forward,
            missingAreaSummary: "Targeted rescan of \(region.name)",
            targetRegionId: region.id
        ))
    }
    
    /// Step 7 & 8: Check new observations and merge if confidence exceeds existing data
    public func checkAndMergeObservations(
        newKeyframes: Int,
        measuredAlignmentResidualM: Double,
        newCoveragePct: Double,
        newQualityScore: Double
    ) -> Bool {
        state = .checkingObservations
        alignmentErrorMeters = measuredAlignmentResidualM
        
        // Safety guard: Reject merge if target region cannot be aligned
        if measuredAlignmentResidualM > relocalizationMaxToleranceMeters {
            state = .alignmentFailed
            statusMessage = "Alignment residual (\(String(format: "%.2f", measuredAlignmentResidualM))m) exceeds tolerance (0.15m). Merge aborted."
            return false
        }
        
        guard let regionId = selectedRegion?.id,
              let idx = availableRegions.firstIndex(where: { $0.id == regionId }) else {
            return false
        }
        
        // Evidence principle: Do not replace reliable observations with lower-confidence data
        if newQualityScore < availableRegions[idx].qualityScore {
            statusMessage = "New observations have lower confidence than existing data. Preserving existing geometry."
            state = .idle
            return false
        }
        
        // Perform non-destructive merge
        availableRegions[idx].coveragePct = max(availableRegions[idx].coveragePct, newCoveragePct)
        availableRegions[idx].qualityScore = max(availableRegions[idx].qualityScore, newQualityScore)
        if availableRegions[idx].coveragePct >= 85.0 && availableRegions[idx].qualityScore >= 90.0 {
            availableRegions[idx].isComplete = true
        }
        availableRegions[idx].isSelectedForRescan = false
        
        state = .mergedSuccess
        rescanKeyframesCollected = newKeyframes
        statusMessage = "Successfully merged \(newKeyframes) observations into \(availableRegions[idx].name). Quality updated to \(Int(availableRegions[idx].qualityScore))%."
        
        // Clear selection
        selectedRegion = nil
        return true
    }
}

