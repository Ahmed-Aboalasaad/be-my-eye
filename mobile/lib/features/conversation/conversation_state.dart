import 'package:flutter/foundation.dart';

import 'audio_playback.dart';
import 'backend_client.dart';
import 'demo_capture.dart';
import 'media_services.dart';
import 'models.dart';

class ConversationState extends ChangeNotifier {
  ConversationState({
    required BackendClient backendClient,
    required MediaCaptureService mediaCaptureService,
    required AudioPlaybackService audioPlaybackService,
    this.debug = false,
  })  : _backendClient = backendClient,
        _mediaCaptureService = mediaCaptureService,
        _audioPlaybackService = audioPlaybackService;

  final BackendClient _backendClient;
  final MediaCaptureService _mediaCaptureService;
  final AudioPlaybackService _audioPlaybackService;
  final bool debug;

  String? _capturedImageBase64;
  String? _capturedAudioBase64;
  String? _lastError;
  ConversationResponse? _lastResponse;
  bool _isBusy = false;

  String? get lastError => _lastError;
  ConversationResponse? get lastResponse => _lastResponse;
  bool get isBusy => _isBusy;

  void loadDemoCapture() {
    _capturedImageBase64 = DemoCapture.imageBase64();
    _capturedAudioBase64 = DemoCapture.audioBase64();
    notifyListeners();
  }

  Future<void> captureImage() async {
    _capturedImageBase64 = await _mediaCaptureService.captureImageBase64();
    notifyListeners();
  }

  Future<void> startAudioRecording() async {
    await _mediaCaptureService.startAudioRecording();
  }

  Future<void> stopAudioRecording() async {
    _capturedAudioBase64 = await _mediaCaptureService.stopAudioRecording();
    notifyListeners();
  }

  Future<void> submit({required String sessionId}) async {
    final imageBase64 = _capturedImageBase64;
    final audioBase64 = _capturedAudioBase64;

    if (imageBase64 == null || audioBase64 == null) {
      _lastError = 'Capture an image and audio before sending.';
      notifyListeners();
      return;
    }

    _isBusy = true;
    _lastError = null;
    notifyListeners();

    try {
      final response = await _backendClient.sendConversation(
        ConversationRequest(
          sessionId: sessionId,
          imageBase64: imageBase64,
          audioBase64: audioBase64,
          debug: debug,
        ),
      );
      _lastResponse = response;
      _lastError = null;
    } catch (error) {
      _lastError = error.toString();
    } finally {
      _isBusy = false;
      notifyListeners();
    }
  }

  Future<void> playLastResponse() async {
    final response = _lastResponse;
    if (response == null) {
      return;
    }
    await _audioPlaybackService.playBase64Audio(response.audioBase64);
  }

  /// Test-only helper: sets lastResponse directly, bypassing submit(), so
  /// widget tests can verify UI reacts to a completed response without
  /// needing a real or fake network round-trip.
  @visibleForTesting
  void debugSetResponseForTest(String text) {
    _lastResponse = ConversationResponse(
      sessionId: 'test-session',
      text: text,
      audioBase64: 'test-audio',
    );
    notifyListeners();
  }
}
