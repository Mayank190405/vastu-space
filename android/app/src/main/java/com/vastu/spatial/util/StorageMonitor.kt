package com.vastu.spatial.util

import android.os.Environment
import android.os.StatFs
import java.io.File

object StorageMonitor {

    private const val CRITICAL_STORAGE_THRESHOLD_MB = 200L
    private const val WARNING_STORAGE_THRESHOLD_MB = 500L

    fun getAvailableStorageBytes(directory: File = Environment.getDataDirectory()): Long {
        return try {
            val stat = StatFs(directory.path)
            stat.availableBlocksLong * stat.blockSizeLong
        } catch (e: Exception) {
            0L
        }
    }

    fun getAvailableStorageMB(directory: File = Environment.getDataDirectory()): Long {
        return getAvailableStorageBytes(directory) / (1024 * 1024)
    }

    fun hasSufficientStorage(minMb: Long = CRITICAL_STORAGE_THRESHOLD_MB, directory: File = Environment.getDataDirectory()): Boolean {
        return getAvailableStorageMB(directory) >= minMb
    }

    fun isStorageLow(directory: File = Environment.getDataDirectory()): Boolean {
        return getAvailableStorageMB(directory) < WARNING_STORAGE_THRESHOLD_MB
    }

    fun formatStorageMB(mb: Long): String {
        return if (mb >= 1024) {
            String.format("%.1f GB", mb / 1024.0)
        } else {
            "$mb MB"
        }
    }
}
