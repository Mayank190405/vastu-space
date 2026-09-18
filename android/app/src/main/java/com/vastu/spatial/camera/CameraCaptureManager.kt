package com.vastu.spatial.camera

import android.annotation.SuppressLint
import android.content.Context
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import androidx.camera.camera2.interop.Camera2CameraControl
import androidx.camera.camera2.interop.CaptureRequestOptions
import androidx.camera.core.Camera
import androidx.camera.core.CameraControl
import androidx.camera.core.CameraSelector
import androidx.camera.core.FocusMeteringAction
import androidx.camera.core.Preview
import androidx.camera.core.SurfaceOrientedMeteringPointFactory
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.video.*
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import com.vastu.spatial.data.model.CameraIntrinsics
import com.vastu.spatial.util.StorageMonitor
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.io.File

class CameraCaptureManager(private val context: Context) {

    private var camera: Camera? = null
    private var videoCapture: VideoCapture<Recorder>? = null
    private var activeRecording: Recording? = null

    private val _isRecording = MutableStateFlow(false)
    val isRecording: StateFlow<Boolean> = _isRecording

    private val _recordedDurationSeconds = MutableStateFlow(0L)
    val recordedDurationSeconds: StateFlow<Long> = _recordedDurationSeconds

    private val _recordingStartTimestampNs = MutableStateFlow(0L)
    val recordingStartTimestampNs: StateFlow<Long> = _recordingStartTimestampNs

    private val _isExposureLocked = MutableStateFlow(false)
    val isExposureLocked: StateFlow<Boolean> = _isExposureLocked

    fun bindCamera(
        lifecycleOwner: LifecycleOwner,
        previewView: PreviewView,
        onInitialized: () -> Unit = {}
    ) {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(context)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(previewView.surfaceProvider)
            }

            // Prefer UHD (4K), fallback to FHD (1080p) or HD (720p)
            val qualitySelector = QualitySelector.fromOrderedList(
                listOf(Quality.UHD, Quality.FHD, Quality.HD),
                FallbackStrategy.lowerQualityOrHigherThan(Quality.FHD)
            )

            val recorder = Recorder.Builder()
                .setQualitySelector(qualitySelector)
                .build()

            videoCapture = VideoCapture.withOutput(recorder)

            // Best wide back camera
            val cameraSelector = CameraSelector.Builder()
                .requireLensFacing(CameraSelector.LENS_FACING_BACK)
                .build()

            try {
                cameraProvider.unbindAll()
                camera = cameraProvider.bindToLifecycle(
                    lifecycleOwner,
                    cameraSelector,
                    preview,
                    videoCapture
                )
                onInitialized()
            } catch (exc: Exception) {
                exc.printStackTrace()
            }
        }, ContextCompat.getMainExecutor(context))
    }

    @SuppressLint("MissingPermission")
    fun startRecording(
        outputFile: File,
        onVideoSaved: (File) -> Unit,
        onError: (String) -> Unit
    ) {
        // Pre-check storage safety
        if (!StorageMonitor.hasSufficientStorage(200, outputFile.parentFile ?: context.filesDir)) {
            onError("Insufficient disk space. At least 200MB required to record.")
            return
        }

        val videoCapture = this.videoCapture ?: run {
            onError("Camera recording engine is not initialized.")
            return
        }

        outputFile.parentFile?.mkdirs()
        val fileOutputOptions = FileOutputOptions.Builder(outputFile).build()

        _recordingStartTimestampNs.value = System.nanoTime()

        activeRecording = videoCapture.output
            .prepareRecording(context, fileOutputOptions)
            .start(ContextCompat.getMainExecutor(context)) { event ->
                when (event) {
                    is VideoRecordEvent.Start -> {
                        _isRecording.value = true
                    }
                    is VideoRecordEvent.Status -> {
                        val durationSec = event.recordingStats.recordedDurationNanos / 1_000_000_000L
                        _recordedDurationSeconds.value = durationSec

                        // Runtime storage guard
                        if (!StorageMonitor.hasSufficientStorage(100, outputFile.parentFile ?: context.filesDir)) {
                            stopRecording()
                            onError("Recording halted automatically: Storage critically low (<100MB)")
                        }
                    }
                    is VideoRecordEvent.Finalize -> {
                        _isRecording.value = false
                        if (!event.hasError()) {
                            onVideoSaved(outputFile)
                        } else {
                            onError("Recording error (code ${event.error})")
                        }
                    }
                }
            }
    }

    fun stopRecording() {
        activeRecording?.stop()
        activeRecording = null
        _isRecording.value = false
    }

    fun toggleExposureLock(lock: Boolean) {
        _isExposureLocked.value = lock
        // AE/AF lock via camera control
        camera?.cameraControl?.let { control ->
            val factory = SurfaceOrientedMeteringPointFactory(1f, 1f)
            val point = factory.createPoint(0.5f, 0.5f)
            val action = FocusMeteringAction.Builder(point)
                .apply {
                    if (lock) {
                        disableAutoCancel()
                    }
                }
                .build()
            control.startFocusAndMetering(action)
        }
    }

    fun extractCameraIntrinsics(): CameraIntrinsics {
        val cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val cameraId = cameraManager.cameraIdList.firstOrNull { id ->
            val characteristics = cameraManager.getCameraCharacteristics(id)
            val facing = characteristics.get(CameraCharacteristics.LENS_FACING)
            facing == CameraCharacteristics.LENS_FACING_BACK
        } ?: cameraManager.cameraIdList.firstOrNull() ?: "0"

        val characteristics = cameraManager.getCameraCharacteristics(cameraId)
        val focalLengths = characteristics.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)
        val sensorSize = characteristics.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE)

        val fMm = focalLengths?.firstOrNull() ?: 4.5f
        val sensorWidthMm = sensorSize?.width ?: 6.4f
        val sensorHeightMm = sensorSize?.height ?: 4.8f

        val width = 1920
        val height = 1080

        val fx = (fMm / sensorWidthMm) * width
        val fy = (fMm / sensorHeightMm) * height
        val cx = width / 2.0
        val cy = height / 2.0

        return CameraIntrinsics(
            fx = fx.toDouble(),
            fy = fy.toDouble(),
            cx = cx,
            cy = cy,
            width = width,
            height = height,
            fps = 30.0
        )
    }
}
