package com.vastu.spatial.data.local

import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.OutputStreamWriter
import java.nio.charset.StandardCharsets

data class JournalEntry(
    val event: String,
    val timestampNs: Long,
    val payload: Map<String, String>
)

class CaptureSessionJournal(private val sessionDir: File) {

    companion object {
        const val JOURNAL_FILENAME = "session_journal.jsonl"
    }

    private val journalFile = File(sessionDir, JOURNAL_FILENAME)

    init {
        if (!sessionDir.exists()) {
            sessionDir.mkdirs()
        }
    }

    @Synchronized
    fun logEvent(event: String, payload: Map<String, String>) {
        val entry = JSONObject().apply {
            put("event", event)
            put("timestamp_ns", System.nanoTime())
            val pObj = JSONObject()
            payload.forEach { (k, v) -> pObj.put(k, v) }
            put("payload", pObj)
        }

        FileOutputStream(journalFile, true).use { fos ->
            OutputStreamWriter(fos, StandardCharsets.UTF_8).use { writer ->
                writer.write(entry.toString() + "\n")
                writer.flush()
                fos.fd.sync() // Guarantee durable fsync
            }
        }
    }

    fun readEvents(): List<JournalEntry> {
        if (!journalFile.exists()) return emptyList()

        val list = mutableListOf<JournalEntry>()
        journalFile.forEachLine(StandardCharsets.UTF_8) { line ->
            if (line.isNotBlank()) {
                try {
                    val obj = JSONObject(line)
                    val pObj = obj.getJSONObject("payload")
                    val map = mutableMapOf<String, String>()
                    pObj.keys().forEach { k -> map[k] = pObj.getString(k) }
                    list.add(
                        JournalEntry(
                            event = obj.getString("event"),
                            timestampNs = obj.getLong("timestamp_ns"),
                            payload = map
                        )
                    )
                } catch (ignored: Exception) { }
            }
        }
        return list
    }
}
