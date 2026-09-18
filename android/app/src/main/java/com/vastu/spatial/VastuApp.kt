package com.vastu.spatial

import android.app.Application
import com.vastu.spatial.data.api.ApiClient
import com.vastu.spatial.data.local.LocalCaptureStorageManager
import com.vastu.spatial.data.local.VastuDatabase
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class VastuApp : Application() {
    companion object {
        lateinit var instance: VastuApp
            private set
    }

    val database by lazy { VastuDatabase.getDatabase(this) }
    val storageManager by lazy { LocalCaptureStorageManager(this) }
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()
        instance = this
        ApiClient.init(this)

        // Recover interrupted / pending captures across app restarts
        applicationScope.launch {
            try {
                storageManager.recoverInterruptedCaptures()
                storageManager.purgeUploadedLocalCaptures(keepLastN = 3)
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
}
