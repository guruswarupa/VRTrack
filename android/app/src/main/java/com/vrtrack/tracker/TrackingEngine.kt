package com.vrtrack.tracker

import android.content.Context
import android.graphics.Bitmap
import android.os.SystemClock
import android.util.Range
import android.util.Size
import androidx.camera.camera2.interop.Camera2Interop
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.core.Delegate
import com.google.mediapipe.tasks.vision.core.ImageProcessingOptions
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.facelandmarker.FaceLandmarker
import com.google.mediapipe.tasks.vision.facelandmarker.FaceLandmarkerResult
import java.util.concurrent.Executors

/**
 * Camera -> MediaPipe face landmarks -> head pose / gaze -> UDP.
 * All processing is on-device; frames are never stored or sent anywhere.
 */
class TrackingEngine(private val app: Context) {
    private val analysisExecutor = Executors.newSingleThreadExecutor()
    private val pose = Pose()
    private val pose2 = Pose()
    private var settings = Settings.load(app)
    private var calib: CalibrationProfile? = CalibrationProfile.load(app)
    private var neutral = Pose().also { n -> calib?.let { c -> n.yaw = c.yaw; n.pitch = c.pitch; n.roll = c.roll; n.x = c.x; n.y = c.y; n.z = c.z } }
    private val calibrator = Calibrator { p -> calib = p; p.save(app); setNeutral(p) }

    // Network status lives in its own fields so the network and camera threads never race on `ui`.
    @Volatile private var link = Link.SEARCHING
    @Volatile private var linkHost = ""
    @Volatile private var latency = -1
    private val net = NetworkClient { l, host, lat -> link = l; linkHost = host; latency = lat }

    private var landmarker: FaceLandmarker? = null
    private var provider: ProcessCameraProvider? = null
    private var bitmap: Bitmap? = null
    private var lastTs = 0L
    private var lastFrameMs = 0L
    private var frameRot = 0
    private var frameAspect = 0.75f

    @Volatile private var ui = UiState(calibrated = calib != null)
    @Volatile var paused = false
    private var fpsCount = 0
    private var fpsWindowStart = 0L
    private var lastPublish = 0L
    private val overlay = FloatArray(OVERLAY.size * 2)
    @Volatile private var running = false

    // ---- lifecycle -------------------------------------------------------------------------

    fun start(owner: LifecycleOwner) {
        if (running) return
        settings = Settings.load(app)
        try {
            landmarker = createLandmarker()
        } catch (e: Exception) {
            ui = ui.copy(error = "Cannot load face model: ${e.message}. Is face_landmarker.task in assets?")
            publish(force = true); return
        }
        running = true
        net.start(settings.host, settings.port)
        ui = ui.copy(running = true, error = null, calibrated = calib != null)
        publish(force = true)
        android.util.Log.i("VRTrack", "engine started")
        bind(owner, null)
    }

    fun stop() {
        running = false
        net.stop()
        ContextCompat.getMainExecutor(app).execute { provider?.unbindAll() }
        landmarker?.close(); landmarker = null
        ui = UiState(calibrated = calib != null); publish(force = true)
    }

    /** Re-bind camera to [owner]; pass a surface provider to show the live preview. */
    fun bind(owner: LifecycleOwner, surface: Preview.SurfaceProvider?) {
        if (!running) return
        val f = ProcessCameraProvider.getInstance(app)
        f.addListener({
            val p = f.get().also { provider = it }
            android.util.Log.i("VRTrack", "binding camera preview=${surface != null}")
            p.unbindAll()
            val (w, h) = Settings.RESOLUTIONS[settings.resolutionIndex]
            val sel = ResolutionSelector.Builder()
                .setResolutionStrategy(ResolutionStrategy(Size(w, h), ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER))
                .build()
            val ab = ImageAnalysis.Builder()
                .setResolutionSelector(sel)
                .setTargetRotation(displayRotation())
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
            // Only request an FPS range the front camera actually supports; an unsupported
            // range makes some HALs deliver no frames at all.
            supportedFpsRange(settings.fps)?.let { r ->
                Camera2Interop.Extender(ab).setCaptureRequestOption(
                    android.hardware.camera2.CaptureRequest.CONTROL_AE_TARGET_FPS_RANGE, r)
            }
            val analysis = ab.build().also { it.setAnalyzer(analysisExecutor, ::analyze); analysisUc = it }
            val uses = mutableListOf<androidx.camera.core.UseCase>(analysis)
            if (surface != null) uses += Preview.Builder().setResolutionSelector(sel).setTargetRotation(displayRotation()).build().also { previewUc = it }.also { it.setSurfaceProvider(surface) }
            try {
                p.bindToLifecycle(owner, CameraSelector.DEFAULT_FRONT_CAMERA, *uses.toTypedArray())
            } catch (e: Exception) {
                ui = ui.copy(error = "Camera error: ${e.message}"); publish(force = true)
            }
        }, ContextCompat.getMainExecutor(app))
    }

    private var analysisUc: ImageAnalysis? = null
    private var previewUc: Preview? = null

    @Suppress("DEPRECATION")
    private fun displayRotation(): Int =
        (app.getSystemService(Context.WINDOW_SERVICE) as android.view.WindowManager).defaultDisplay.rotation

    /** Phone turned (portrait <-> landscape): keep frames upright so head pose stays in world axes. */
    fun updateRotation() {
        val r = displayRotation()
        analysisUc?.targetRotation = r
        previewUc?.targetRotation = r
    }

    private fun supportedFpsRange(fps: Int): Range<Int>? = try {
        val cm = app.getSystemService(Context.CAMERA_SERVICE) as android.hardware.camera2.CameraManager
        val id = cm.cameraIdList.first {
            cm.getCameraCharacteristics(it).get(android.hardware.camera2.CameraCharacteristics.LENS_FACING) ==
                android.hardware.camera2.CameraCharacteristics.LENS_FACING_FRONT }
        cm.getCameraCharacteristics(id)
            .get(android.hardware.camera2.CameraCharacteristics.CONTROL_AE_AVAILABLE_TARGET_FPS_RANGES)
            ?.filter { it.upper == fps }?.minByOrNull { it.lower }
    } catch (_: Exception) { null }

    private fun createLandmarker(): FaceLandmarker {
        fun build(delegate: Delegate) = FaceLandmarker.createFromOptions(app,
            FaceLandmarker.FaceLandmarkerOptions.builder()
                .setBaseOptions(BaseOptions.builder().setModelAssetPath(MODEL).setDelegate(delegate).build())
                .setRunningMode(RunningMode.LIVE_STREAM)
                .setNumFaces(1)
                .setOutputFaceBlendshapes(settings.eyeTracking)   // only needed for blink detection
                .setOutputFacialTransformationMatrixes(true)
                .setResultListener(::onResult)
                .setErrorListener { e -> ui = ui.copy(error = e.message); publish(force = true) }
                .build())
        return try { build(Delegate.GPU).also { android.util.Log.i("VRTrack", "face model: GPU delegate") } }
        catch (e: Exception) { android.util.Log.i("VRTrack", "face model: CPU delegate (GPU failed: ${e.message})"); build(Delegate.CPU) }
    }

    // ---- user actions ----------------------------------------------------------------------

    fun applySettings(s: Settings, owner: LifecycleOwner?) {
        val camChanged = s.resolutionIndex != settings.resolutionIndex || s.fps != settings.fps
        val netChanged = s.host != settings.host || s.port != settings.port
        settings = s; s.save(app)
        if (running && netChanged) net.start(s.host, s.port)
        if (running && camChanged && owner != null) bind(owner, null)
    }

    fun startCalibration() { if (running) calibrator.start(settings.eyeTracking) }
    fun cancelCalibration() = calibrator.cancel()

    /** Use the current head pose as the new centre. */
    fun recenter() {
        neutral.yaw = lastRaw.yaw; neutral.pitch = lastRaw.pitch; neutral.roll = lastRaw.roll
        neutral.x = lastRaw.x; neutral.y = lastRaw.y; neutral.z = lastRaw.z
    }

    private fun setNeutral(c: CalibrationProfile) {
        neutral.yaw = c.yaw; neutral.pitch = c.pitch; neutral.roll = c.roll
        neutral.x = c.x; neutral.y = c.y; neutral.z = c.z
    }

    // ---- frame path ------------------------------------------------------------------------

    private fun analyze(img: ImageProxy) {
        try {
            val lm = landmarker ?: return
            if (frameCount++ % 60 == 0) android.util.Log.i("VRTrack", "frames=$frameCount")
            val now = SystemClock.uptimeMillis()
            if (now - lastFrameMs < 1000L / settings.fps - 4) return
            lastFrameMs = now
            val w = img.width; val h = img.height
            var bmp = bitmap
            if (bmp == null || bmp.width != w || bmp.height != h) {
                bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888); bitmap = bmp
            }
            val plane = img.planes[0]
            if (plane.rowStride == w * 4) {
                plane.buffer.rewind(); bmp.copyPixelsFromBuffer(plane.buffer)
            } else {
                img.toBitmap().let { b -> bmp.eraseColor(0); android.graphics.Canvas(bmp).drawBitmap(b, 0f, 0f, null) }
            }
            frameRot = img.imageInfo.rotationDegrees
            frameAspect = if (frameRot % 180 == 0) w.toFloat() / h else h.toFloat() / w
            val ts = maxOf(now, lastTs + 1); lastTs = ts
            lm.detectAsync(BitmapImageBuilder(bmp).build(),
                ImageProcessingOptions.builder().setRotationDegrees(frameRot).build(), ts)
        } finally { img.close() }
    }

    private var frameCount = 0
    private val lastRaw = Pose()

    private fun onResult(r: FaceLandmarkerResult, @Suppress("UNUSED_PARAMETER") input: com.google.mediapipe.framework.image.MPImage) {
        val faces = r.faceLandmarks()
        val matrices = r.facialTransformationMatrixes()
        val ok = faces.isNotEmpty() && matrices.isPresent && matrices.get().isNotEmpty() &&
            PoseMath.fromMatrix(matrices.get()[0], pose)
        fpsCount++
        val now = SystemClock.elapsedRealtime()
        if (now - fpsWindowStart >= 1000) {
            ui = ui.copy(fps = fpsCount); fpsCount = 0; fpsWindowStart = now
        }
        var flags = 0
        var gx = 0f; var gy = 0f; var conf = 0f
        if (paused) flags = flags or Protocol.FLAG_PAUSED
        if (ok) {
            val lms = faces[0]
            lastRaw.yaw = pose.yaw; lastRaw.pitch = pose.pitch; lastRaw.roll = pose.roll
            lastRaw.x = pose.x; lastRaw.y = pose.y; lastRaw.z = pose.z
            var minX = 1f; var maxX = 0f; var minY = 1f; var maxY = 0f
            for (i in OVERLAY.indices) {
                val l = lms[OVERLAY[i]]
                overlay[i * 2] = l.x(); overlay[i * 2 + 1] = l.y()
                minX = minOf(minX, l.x()); maxX = maxOf(maxX, l.x())
                minY = minOf(minY, l.y()); maxY = maxOf(maxY, l.y())
            }
            conf = quality(minX, maxX, minY, maxY)

            var leftOpen = true; var rightOpen = true
            var rawGx = 0f; var rawGy = 0f
            if (settings.eyeTracking && lms.size > 477) {
                flags = flags or Protocol.FLAG_EYES_ENABLED
                val g = gazeRaw(lms)
                rawGx = g[0]; rawGy = g[1]
                r.faceBlendshapes().ifPresent { bs ->
                    if (bs.isNotEmpty()) for (c in bs[0]) when (c.categoryName()) {
                        "eyeBlinkLeft" -> leftOpen = c.score() < BLINK
                        "eyeBlinkRight" -> rightOpen = c.score() < BLINK
                    }
                }
                val cp = calib
                gx = if (cp != null) cp.normGazeX(rawGx) else 0f
                gy = if (cp != null) cp.normGazeY(rawGy) else 0f
            }
            if (!paused) flags = flags or Protocol.FLAG_TRACKING
            if (leftOpen) flags = flags or Protocol.FLAG_LEFT_OPEN
            if (rightOpen) flags = flags or Protocol.FLAG_RIGHT_OPEN
            if (calibrator.active) { calibrator.feed(pose, rawGx, rawGy) }

            // pose relative to the neutral/centre pose
            pose2.yaw = pose.yaw - neutral.yaw; pose2.pitch = pose.pitch - neutral.pitch
            pose2.roll = pose.roll - neutral.roll
            pose2.x = pose.x - neutral.x; pose2.y = pose.y - neutral.y; pose2.z = pose.z - neutral.z
            if (!paused) net.sendPose(flags, pose2, gx, gy, conf)
            else net.sendPose(flags, pose2, 0f, 0f, 0f)
            ui = ui.copy(face = true, paused = paused, confidence = conf,
                yaw = pose2.yaw, pitch = pose2.pitch, roll = pose2.roll,
                x = pose2.x, y = pose2.y, z = pose2.z, gazeX = gx, gazeY = gy,
                leftOpen = leftOpen, rightOpen = rightOpen,
                calStep = calibrator.step, calProgress = calibrator.progress,
                calibrated = calib != null, frameAspect = frameAspect)
            publish(landmarks = overlay)
        } else {
            // Face lost / occluded: tell the PC so it holds the last pose. Never invent values.
            net.sendPose(flags, ZERO, 0f, 0f, 0f)
            ui = ui.copy(face = false, paused = paused, confidence = 0f, calStep = calibrator.step,
                calProgress = calibrator.progress, frameAspect = frameAspect, landmarks = FloatArray(0))
            publish()
        }
    }

    private fun quality(minX: Float, maxX: Float, minY: Float, maxY: Float): Float {
        val margin = minOf(minX, minY, 1f - maxX, 1f - maxY)   // face clipped by frame edge
        val size = maxOf(maxX - minX, maxY - minY)             // face too small = noisy pose
        val edge = (margin / 0.04f).coerceIn(0f, 1f)
        val sz = (size / 0.25f).coerceIn(0f, 1f)
        return minOf(edge, sz)
    }

    /** Raw iris position ratios relative to eye corners / lids, averaged over both eyes. */
    private fun gazeRaw(l: List<com.google.mediapipe.tasks.components.containers.NormalizedLandmark>): FloatArray {
        fun eye(outer: Int, inner: Int, up: Int, low: Int, iris: Int): FloatArray {
            val ox = l[outer].x(); val ix = l[inner].x()
            val w = ix - ox
            val gx = if (kotlin.math.abs(w) < 1e-5f) 0f else (l[iris].x() - (ox + ix) / 2f) / kotlin.math.abs(w)
            val uy = l[up].y(); val ly = l[low].y()
            val hh = ly - uy
            val gy = if (kotlin.math.abs(hh) < 1e-5f) 0f else ((uy + ly) / 2f - l[iris].y()) / kotlin.math.abs(hh)
            return floatArrayOf(gx, gy)
        }
        val a = eye(33, 133, 159, 145, 468)
        val b = eye(263, 362, 386, 374, 473)
        // both ratios are measured in image-space (iris moving image-right = positive)
        return floatArrayOf((a[0] + b[0]) / 2f, (a[1] + b[1]) / 2f)
    }

    private fun publish(force: Boolean = false, landmarks: FloatArray? = null) {
        val now = SystemClock.elapsedRealtime()
        if (!force && now - lastPublish < 66) return
        lastPublish = now
        TrackerState.ui.value = ui.copy(landmarks = landmarks?.copyOf() ?: ui.landmarks,
            link = link, host = linkHost, latencyMs = latency)
    }

    companion object {
        const val MODEL = "face_landmarker.task"
        private const val BLINK = 0.5f
        private val ZERO = Pose()
        private val OVAL = intArrayOf(10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378,
            400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109)
        private val EYES = intArrayOf(33, 160, 158, 133, 153, 144, 362, 385, 387, 263, 373, 380)
        private val IRIS = intArrayOf(468, 469, 470, 471, 472, 473, 474, 475, 476, 477)
        private val NOSE = intArrayOf(1)
        val OVERLAY = OVAL + EYES + IRIS + NOSE
        val OVAL_COUNT = OVAL.size
        val EYE_COUNT = EYES.size
        val IRIS_COUNT = IRIS.size
    }
}
