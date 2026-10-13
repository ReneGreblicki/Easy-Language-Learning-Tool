package __APP_PACKAGE__

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.Locale
import java.util.UUID
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/** Uses public Android APIs; every initialization and utterance has a deadline. */
class AppSpeechPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {
    private lateinit var context: Context
    private lateinit var channel: MethodChannel
    private val main = Handler(Looper.getMainLooper())
    private var tts: TextToSpeech? = null
    private var selectedEngine: String? = null
    private var ready = false
    private var detached = false
    private var initGeneration = 0
    private var initFailure: String? = null
    private val waiting = mutableListOf<Pair<MethodCall, MethodChannel.Result>>()
    private data class Speech(val result: MethodChannel.Result, val completion: Boolean)
    private val requests = mutableMapOf<String, Speech>()
    private var awaitCompletion = false
    private var volume = 1.0f
    private var activeId: String? = null
    private var focusRequest: AudioFocusRequest? = null
    private val attributes = AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_MEDIA)
        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        channel = MethodChannel(binding.binaryMessenger, "easy_language_learning_tool/native_speech")
        channel.setMethodCallHandler(this)
        initialize(context.getSharedPreferences("speech", Context.MODE_PRIVATE).getString("engine", null))
    }

    private fun initialize(engine: String?) {
        selectedEngine = engine
        val generation = ++initGeneration
        ready = false
        initFailure = null
        tts?.shutdown()
        val listener = TextToSpeech.OnInitListener { status -> main.post {
            if (detached || generation != initGeneration) return@post
            if (status != TextToSpeech.SUCCESS) {
                failInitialization("Android could not initialize ${engine ?: "the system TTS engine"} (status $status).")
                return@post
            }
            // Install callbacks BEFORE releasing queued calls; the plugin we
            // previously used did this after releasing its initialization queue.
            tts?.setOnUtteranceProgressListener(progress)
            tts?.setAudioAttributes(attributes)
            ready = true
            val calls = waiting.toList()
            waiting.clear()
            calls.forEach { onMethodCall(it.first, it.second) }
        } }
        tts = if (engine == null) TextToSpeech(context, listener)
              else TextToSpeech(context, listener, engine)
        main.postDelayed({
            if (!ready && !detached && generation == initGeneration && initFailure == null) {
                failInitialization("The TTS engine did not initialize within 8 seconds. Try another installed engine in Test voice.")
            }
        }, 8000)
    }

    private fun failInitialization(message: String) {
        initFailure = message
        val calls = waiting.toList()
        waiting.clear()
        calls.forEach { it.second.error("TTS_INIT_FAILED", message, null) }
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        if (call.method == "getEngines") {
            result.success(tts?.engines?.map { it.name } ?: emptyList<String>())
            return
        }
        if (call.method == "getDefaultEngine") {
            result.success(selectedEngine ?: tts?.defaultEngine ?: "Not initialized")
            return
        }
        if (call.method == "setEngine") {
            val engine = call.arguments as? String
            if (engine.isNullOrBlank()) {
                result.error("TTS_ENGINE_INVALID", "Choose an installed engine.", null)
                return
            }
            cancelSpeech()
            waiting.add(Pair(MethodCall("engineReady", engine), result))
            initialize(engine)
            return
        }
        if (call.method == "stop") {
            cancelSpeech()
            tts?.stop()
            result.success(1)
            return
        }
        if (!ready) {
            val error = initFailure
            if (error != null) result.error("TTS_INIT_FAILED", error, null)
            else waiting.add(Pair(call, result))
            return
        }
        val engine = tts!!
        try {
            when (call.method) {
                "engineReady" -> {
                    context.getSharedPreferences("speech", Context.MODE_PRIVATE).edit()
                        .putString("engine", call.arguments as String).apply()
                    result.success(1)
                }
                "getLanguages" -> result.success(engine.availableLanguages?.map { it.toLanguageTag() } ?: emptyList<String>())
                "getVoices" -> result.success(engine.voices?.map { voice -> mapOf(
                    "name" to voice.name, "locale" to voice.locale.toLanguageTag(),
                    "network_required" to voice.isNetworkConnectionRequired.toString(),
                    "features" to (voice.features ?: emptySet<String>()).toList()
                ) } ?: emptyList<Map<String, Any>>())
                "setLanguage" -> {
                    val locale = Locale.forLanguageTag((call.arguments as String).replace('_', '-'))
                    val status = engine.setLanguage(locale)
                    if (status < 0) result.error("TTS_LANGUAGE_UNAVAILABLE", "${locale.toLanguageTag()} voice data is missing or unsupported by ${engine.defaultEngine} (status $status). Install voice data in Android text-to-speech settings.", null)
                    else result.success(1)
                }
                "setVoice" -> {
                    val name = call.argument<String>("name")
                    val voice = engine.voices?.firstOrNull { it.name == name }
                    result.success(if (voice != null && engine.setVoice(voice) == TextToSpeech.SUCCESS) 1 else 0)
                }
                "setVolume" -> { volume = (call.arguments as Number).toFloat().coerceIn(0f, 1f); result.success(1) }
                "setSpeechRate" -> result.success(if (engine.setSpeechRate((call.arguments as Number).toFloat() * 2f) == TextToSpeech.SUCCESS) 1 else 0)
                "awaitSpeakCompletion" -> { awaitCompletion = call.arguments as Boolean; result.success(1) }
                "speak" -> speak(call, result)
                else -> result.notImplemented()
            }
        } catch (error: Exception) {
            result.error("TTS_PLATFORM_ERROR", error.message ?: error.javaClass.simpleName, null)
        }
    }

    private fun speak(call: MethodCall, result: MethodChannel.Result) {
        val text = call.argument<String>("text")?.trim().orEmpty()
        if (text.isEmpty()) { result.success(1); return }
        cancelSpeech()
        tts?.stop()
        if (call.argument<Boolean>("focus") == true) requestFocus()
        val id = UUID.randomUUID().toString()
        activeId = id
        requests[id] = Speech(result, awaitCompletion)
        val params = Bundle().apply { putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, volume) }
        val status = tts!!.speak(text, TextToSpeech.QUEUE_FLUSH, params, id)
        if (status != TextToSpeech.SUCCESS) {
            finish(id, "TTS_SPEAK_REJECTED", "${selectedEngine ?: tts?.defaultEngine} rejected speech (status $status). Try another engine in Test voice.")
            return
        }
        val waitMs = if (awaitCompletion) (text.length / 8).coerceIn(15, 120) * 1000L else 8000L
        main.postDelayed({
            if (requests.containsKey(id)) {
                tts?.stop()
                finish(id, "TTS_PLAYBACK_TIMEOUT", "${selectedEngine ?: tts?.defaultEngine} did not ${if (awaitCompletion) "finish" else "start"} speech. Try another engine in Test voice.")
            }
        }, waitMs)
    }

    private val progress = object : UtteranceProgressListener() {
        override fun onStart(id: String) { main.post {
            val request = requests[id]
            if (request != null && !request.completion) finish(id)
        } }
        override fun onDone(id: String) { main.post { finish(id); releaseFocus(id) } }
        @Deprecated("Android callback")
        override fun onError(id: String) { onError(id, TextToSpeech.ERROR) }
        override fun onError(id: String, code: Int) { main.post {
            finish(id, "TTS_SYNTHESIS_FAILED", "${selectedEngine ?: tts?.defaultEngine} could not produce speech (error $code). Check voice data or try another engine in Test voice.")
            releaseFocus(id)
        } }
        override fun onStop(id: String, interrupted: Boolean) { main.post {
            finish(id, "TTS_CANCELLED", "Speech was stopped.")
            releaseFocus(id)
        } }
    }

    private fun finish(id: String, code: String? = null, message: String? = null) {
        val request = requests.remove(id) ?: return
        if (code == null) request.result.success(1)
        else { request.result.error(code, message, null); releaseFocus(id) }
    }

    private fun cancelSpeech() {
        requests.keys.toList().forEach { finish(it, "TTS_CANCELLED", "Speech was stopped.") }
        releaseFocus(activeId)
    }

    private fun requestFocus() {
        val manager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        if (Build.VERSION.SDK_INT >= 26) {
            val request = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                .setAudioAttributes(attributes).setOnAudioFocusChangeListener { }.build()
            focusRequest = request
            manager.requestAudioFocus(request)
        } else {
            @Suppress("DEPRECATION")
            manager.requestAudioFocus(null, AudioManager.STREAM_MUSIC, AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
        }
    }

    private fun releaseFocus(id: String?) {
        if (id != activeId) return
        val manager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        if (Build.VERSION.SDK_INT >= 26) focusRequest?.let { manager.abandonAudioFocusRequest(it) }
        else {
            @Suppress("DEPRECATION")
            manager.abandonAudioFocus(null)
        }
        focusRequest = null
        activeId = null
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        detached = true
        ++initGeneration
        cancelSpeech()
        failInitialization("Speech engine was closed.")
        tts?.stop()
        tts?.shutdown()
        channel.setMethodCallHandler(null)
    }
}
