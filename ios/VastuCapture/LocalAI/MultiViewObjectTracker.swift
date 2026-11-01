import Foundation

/// Multi-view temporal object tracker fusing multi-angle furniture observations
public final class MultiViewObjectTracker {
    public static let shared = MultiViewObjectTracker()
    
    private var activeTracks: [TrackedFurnitureObject] = []
    private let lock = NSLock()
    private let maxAssociationDistanceM: Double = 0.90 // 90cm spatial gating threshold
    
    public init() {}
    
    public func reset() {
        lock.lock()
        defer { lock.unlock() }
        activeTracks.removeAll()
    }
    
    /// Incorporates a new 3D detection estimate into multi-view object tracking
    public func update(
        detection: DetectedFurniture,
        estimate: PositionEstimate3D,
        timestamp: TimeInterval
    ) {
        lock.lock()
        defer { lock.unlock() }
        
        let newPos = estimate.position
        var bestIndex: Int? = nil
        var bestDist = Double.infinity
        
        // 1. Data Association: Find existing track of matching category within spatial gate
        for (idx, track) in activeTracks.enumerated() {
            guard track.category == detection.category || track.category == .unknown || detection.category == .unknown else {
                continue
            }
            
            let dx = track.position3D.x - newPos.x
            let dy = track.position3D.y - newPos.y
            let dz = track.position3D.z - newPos.z
            let dist = sqrt(dx * dx + dy * dy + dz * dz)
            
            if dist < maxAssociationDistanceM && dist < bestDist {
                bestDist = dist
                bestIndex = idx
            }
        }
        
        // 2. State Update
        if let idx = bestIndex {
            var track = activeTracks[idx]
            track.observationCount += 1
            track.lastSeenTimestamp = timestamp
            
            // Recursive Bayesian weighted average for position refinement
            let weight = 1.0 / Double(min(track.observationCount, 12))
            let updatedX = track.position3D.x * (1.0 - weight) + newPos.x * weight
            let updatedY = track.position3D.y * (1.0 - weight) + newPos.y * weight
            let updatedZ = track.position3D.z * (1.0 - weight) + newPos.z * weight
            track.position3D = Point3D(x: updatedX, y: updatedY, z: updatedZ)
            
            // Refine ground contact
            track.groundContact = Point2D(x: updatedX, z: updatedZ)
            
            // Uncertainty decreases with multi-view observations
            track.uncertaintyMeters = max(0.08, track.uncertaintyMeters * 0.85)
            track.confidence = min(0.98, max(track.confidence, detection.confidence) + 0.05)
            
            // Becomes stable after 3 consistent observations
            if track.observationCount >= 3 {
                track.isStable = true
            }
            
            activeTracks[idx] = track
        } else {
            // Create new candidate track
            let newTrack = TrackedFurnitureObject(
                category: detection.category,
                label: detection.label,
                confidence: detection.confidence,
                position3D: newPos,
                dimensions: estimate.dimensions,
                uncertaintyMeters: estimate.uncertaintyRadiusMeters,
                groundContact: estimate.groundContactPoint,
                observationCount: 1,
                firstSeenTimestamp: timestamp,
                lastSeenTimestamp: timestamp,
                isStable: false
            )
            activeTracks.append(newTrack)
        }
        
        // 3. Prune stale unconfirmed tracks (older than 10s with only 1 observation)
        activeTracks.removeAll { track in
            if !track.isStable && track.observationCount <= 1 {
                return (timestamp - track.lastSeenTimestamp) > 10.0
            }
            return false
        }
    }
    
    /// Returns all tracked furniture objects (filtering unconfirmed single-frame noise if requested)
    public func getTrackedObjects(onlyStable: Bool = false) -> [TrackedFurnitureObject] {
        lock.lock()
        defer { lock.unlock() }
        
        if onlyStable {
            return activeTracks.filter { $0.isStable }
        }
        return activeTracks
    }
}

