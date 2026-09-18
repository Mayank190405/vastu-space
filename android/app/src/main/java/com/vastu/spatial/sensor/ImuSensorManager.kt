package com.vastu.spatial.sensor

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.io.BufferedWriter
import java.io.File
import java.io.FileWriter
import kotlin.math.sqrt

enum class MotionQuality {
    OPTIMAL,
    TOO_FAST,
    SHAKY,
    STATIONARY
}

class ImuSensorManager(context: Context) : SensorEventListener {

    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val accelerometer: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
    private val gyroscope: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)

    private var imuWriter: BufferedWriter? = null
    private var isRecording = false

    private val _motionQuality = MutableStateFlow(MotionQuality.OPTIMAL)
    val motionQuality: StateFlow<MotionQuality> = _motionQuality

    private val _sampleCount = MutableStateFlow(0L)
    val sampleCount: StateFlow<Long> = _sampleCount

    // Temporary storage for sensor values and accuracy
    private var latestAccel = FloatArray(3)
    private var latestGyro = FloatArray(3)
    private var accelAccuracy = 0
    private var gyroAccuracy = 0
    private var lastRecordedNs = 0L

    // 100 Hz = 10,000,000 nanoseconds interval (10ms)
    private val targetIntervalNs = 10_000_000L

    fun isAvailable(): Boolean {
        return accelerometer != null && gyroscope != null
    }

    fun hasAccelerometer(): Boolean = accelerometer != null
    fun hasGyroscope(): Boolean = gyroscope != null

    fun startRecording(outputFile: File) {
        if (isRecording) return

        outputFile.parentFile?.mkdirs()
        imuWriter = BufferedWriter(FileWriter(outputFile, false))
        
        // CSV Header with sensor_type and accuracy
        imuWriter?.write("timestamp_ns,sensor_type,x,y,z,accuracy\n")

        _sampleCount.value = 0L
        isRecording = true
        lastRecordedNs = 0L

        // Register at 10,000 microseconds (100Hz)
        accelerometer?.let {
            sensorManager.registerListener(this, it, 10000)
        }
        gyroscope?.let {
            sensorManager.registerListener(this, it, 10000)
        }
    }

    fun stopRecording() {
        if (!isRecording) return
        isRecording = false
        sensorManager.unregisterListener(this)

        try {
            imuWriter?.flush()
            imuWriter?.close()
        } catch (e: Exception) {
            e.printStackTrace()
        } finally {
            imuWriter = null
        }
    }

    override fun onSensorChanged(event: SensorEvent?) {
        if (event == null || !isRecording) return

        when (event.sensor.type) {
            Sensor.TYPE_ACCELEROMETER -> {
                System.arraycopy(event.values, 0, latestAccel, 0, 3)
                accelAccuracy = event.accuracy
            }
            Sensor.TYPE_GYROSCOPE -> {
                System.arraycopy(event.values, 0, latestGyro, 0, 3)
                gyroAccuracy = event.accuracy
            }
        }

        val currentNs = event.timestamp
        if (currentNs - lastRecordedNs >= targetIntervalNs) {
            lastRecordedNs = currentNs

            val ax = latestAccel[0]
            val ay = latestAccel[1]
            val az = latestAccel[2]
            val gx = latestGyro[0]
            val gy = latestGyro[1]
            val gz = latestGyro[2]

            // Calculate rotational velocity magnitude
            val gyroMag = sqrt((gx * gx + gy * gy + gz * gz).toDouble())

            _motionQuality.value = when {
                gyroMag > 1.8 -> MotionQuality.SHAKY
                gyroMag > 0.8 -> MotionQuality.TOO_FAST
                gyroMag < 0.02 -> MotionQuality.STATIONARY
                else -> MotionQuality.OPTIMAL
            }

            try {
                // Log Accelerometer sample
                imuWriter?.write("$currentNs,ACCELEROMETER,$ax,$ay,$az,$accelAccuracy\n")
                // Log Gyroscope sample
                imuWriter?.write("$currentNs,GYROSCOPE,$gx,$gy,$gz,$gyroAccuracy\n")
                _sampleCount.value += 2
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        when (sensor?.type) {
            Sensor.TYPE_ACCELEROMETER -> accelAccuracy = accuracy
            Sensor.TYPE_GYROSCOPE -> gyroAccuracy = accuracy
        }
    }
}
