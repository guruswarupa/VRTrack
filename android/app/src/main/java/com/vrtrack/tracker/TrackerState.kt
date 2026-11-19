package com.vrtrack.tracker

import kotlinx.coroutines.flow.MutableStateFlow

/** Snapshot rendered by the UI. Updated at most ~15x/s to keep the UI thread cheap. */
data class UiState(
    val running: Boolean = false,
    val paused: Boolean = false,
    val face: Boolean = false,
    val confidence: Float = 0f,
    val fps: Int = 0,
    val link: Link = Link.SEARCHING,
    val host: String = "",
    val latencyMs: Int = -1,
    val calStep: CalStep = CalStep.IDLE,
    val calProgress: Float = 0f,
    val calibrated: Boolean = false,
    val yaw: Float = 0f, val pitch: Float = 0f, val roll: Float = 0f,
    val x: Float = 0f, val y: Float = 0f, val z: Float = 0f,
    val gazeX: Float = 0f, val gazeY: Float = 0f,
    val leftOpen: Boolean = true, val rightOpen: Boolean = true,
    /** Overlay points as normalised x,y pairs in upright (non-mirrored) image space. */
    val landmarks: FloatArray = FloatArray(0),
    val frameAspect: Float = 0.75f, // width / height of the upright frame
    val error: String? = null,
)

object TrackerState {
    val ui = MutableStateFlow(UiState())
}
