import Foundation
import AVFoundation
import CoreVideo
import CoreImage
import ImageIO
import UniformTypeIdentifiers

public final class CameraFrameRecorder {
    public let framesDirectory: URL
    public var compressionQuality: Float = 0.85
    
    private var videoWriter: AVAssetWriter?
    private var videoInput: AVAssetWriterInput?
    private var videoAdaptor: AVAssetWriterInputPixelBufferAdaptor?
    private var firstVideoTimestamp: Double?
    private var videoFailure: Error?
    public var videoURL: URL { framesDirectory.deletingLastPathComponent().appendingPathComponent("capture.mp4") }

    private let context = CIContext(options: [.useSoftwareRenderer: false])
    private let encodeQueue = DispatchQueue(label: "com.vastu.capture.frame_encoder", qos: .userInitiated)
    private let queueSemaphore = DispatchSemaphore(value: 4) // Limit outstanding asynchronous encoding tasks to 4 frames
    
    public private(set) var recordedFrameCount: Int = 0
    public private(set) var droppedFrameCount: Int = 0
    
    public init(framesDirectory: URL) throws {
        self.framesDirectory = framesDirectory
        try FileManager.default.createDirectory(at: framesDirectory, withIntermediateDirectories: true)
    }
    
    /// Asynchronously compresses pixelBuffer to JPEG and saves to disk as sequential frame file.
    /// Non-blocking: Drops frame if queue is backpressured to preserve live ARKit tracking frame rate.
    public func recordFrame(
        pixelBuffer: CVPixelBuffer,
        frameIndex: Int,
        completion: ((_ frameId: String, _ success: Bool) -> Void)? = nil
    ) {
        let captureTimestamp = ProcessInfo.processInfo.systemUptime
        let frameId = String(format: "frame_%06d.jpg", frameIndex)
        let destinationURL = framesDirectory.appendingPathComponent(frameId)
        
        // Retain pixel buffer for background encoding
        CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
        
        // Fast tryWait to prevent encoder backpressure from lagging ARKit
        guard queueSemaphore.wait(timeout: .now()) == .success else {
            CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly)
            droppedFrameCount += 1
            completion?(frameId, false)
            return
        }
        
        encodeQueue.async { [weak self] in
            guard let self = self else {
                CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly)
                return
            }
            defer {
                CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly)
                self.queueSemaphore.signal()
            }
            
            do {
                if self.videoWriter == nil {
                    let writer = try AVAssetWriter(outputURL: self.videoURL, fileType: .mp4)
                    let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
                        AVVideoCodecKey: AVVideoCodecType.h264,
                        AVVideoWidthKey: CVPixelBufferGetWidth(pixelBuffer),
                        AVVideoHeightKey: CVPixelBufferGetHeight(pixelBuffer)
                    ])
                    input.expectsMediaDataInRealTime = true
                    guard writer.canAdd(input) else { throw NSError(domain: "VideoCapture", code: 1) }
                    writer.add(input)
                    self.videoAdaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: nil)
                    self.videoWriter = writer
                    self.videoInput = input
                    guard writer.startWriting() else { throw writer.error ?? NSError(domain: "VideoCapture", code: 2) }
                    writer.startSession(atSourceTime: .zero)
                    self.firstVideoTimestamp = captureTimestamp
                }
                if self.videoInput?.isReadyForMoreMediaData == true {
                    let time = CMTime(seconds: captureTimestamp - (self.firstVideoTimestamp ?? captureTimestamp), preferredTimescale: 600)
                    if self.videoAdaptor?.append(pixelBuffer, withPresentationTime: time) != true {
                        throw self.videoWriter?.error ?? NSError(domain: "VideoCapture", code: 3)
                    }
                }
            } catch { self.videoFailure = error }

            let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
            guard let cgImage = self.context.createCGImage(ciImage, from: ciImage.extent) else {
                self.droppedFrameCount += 1
                completion?(frameId, false)
                return
            }
            
            guard let dest = CGImageDestinationCreateWithURL(destinationURL as CFURL, UTType.jpeg.identifier as CFString, 1, nil) else {
                self.droppedFrameCount += 1
                completion?(frameId, false)
                return
            }
            
            let options: [CFString: Any] = [
                kCGImageDestinationLossyCompressionQuality: self.compressionQuality,
                kCGImagePropertyOrientation: 1 // Default up
            ]
            
            CGImageDestinationAddImage(dest, cgImage, options as CFDictionary)
            if CGImageDestinationFinalize(dest) {
                self.recordedFrameCount += 1
                completion?(frameId, true)
            } else {
                self.droppedFrameCount += 1
                completion?(frameId, false)
            }
        }
    }
    
    public func finishVideo() throws {
        flush()
        if let failure = videoFailure { throw failure }
        guard let writer = videoWriter, let input = videoInput else {
            throw NSError(domain: "VideoCapture", code: 4, userInfo: [NSLocalizedDescriptionKey: "No video frames were recorded"])
        }
        input.markAsFinished()
        let finished = DispatchSemaphore(value: 0)
        writer.finishWriting { finished.signal() }
        guard finished.wait(timeout: .now() + 30) == .success, writer.status == .completed else {
            throw writer.error ?? NSError(domain: "VideoCapture", code: 5, userInfo: [NSLocalizedDescriptionKey: "Video encoding did not finish"])
        }
    }

    /// Flushes any pending encode operations before package finalization.
    public func flush() {
        encodeQueue.sync {}
    }
}

