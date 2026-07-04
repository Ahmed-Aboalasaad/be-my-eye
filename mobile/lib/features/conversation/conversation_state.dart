import 'package:flutter/foundation.dart';

import 'audio_playback.dart';
import 'backend_client.dart';
import 'demo_capture.dart';
import 'media_services.dart';
import 'models.dart';
import 'os_tts_fallback.dart';

class ConversationState extends ChangeNotifier {
  ConversationState({
    required BackendClient backendClient,
    required MediaCaptureService mediaCaptureService,
    required AudioPlaybackService audioPlaybackService,
    required OsTtsFallbackService osTtsFallbackService,
    this.debug = false,
  })  : _backendClient = backendClient,
        _mediaCaptureService = mediaCaptureService,
        _audioPlaybackService = audioPlaybackService,
        _osTtsFallbackService = osTtsFallbackService;

  final BackendClient _backendClient;
  final MediaCaptureService _mediaCaptureService;
  final AudioPlaybackService _audioPlaybackService;
  final OsTtsFallbackService _osTtsFallbackService;
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

  /// Always the first call of a new hold-to-ask gesture, so this is where
  /// the previous turn's error and answer get cleared for the new attempt.
  /// The later steps in the same gesture must not clobber an error this
  /// step (or each other) already recorded -- see [startAudioRecording] and
  /// [stopAudioRecording].
  Future<void> captureImage() async {
    _lastError = null;
    _lastResponse = null;
    try {
      _capturedImageBase64 = await _mediaCaptureService.captureImageBase64();
    } catch (error) {
      _lastError = 'Could not access the camera: $error';
    }
    notifyListeners();
  }

  Future<void> startAudioRecording() async {
    try {
      await _mediaCaptureService.startAudioRecording();
    } catch (error) {
      _lastError ??= 'Could not start recording: $error';
    }
    notifyListeners();
  }

  Future<void> stopAudioRecording() async {
    try {
      _capturedAudioBase64 = await _mediaCaptureService.stopAudioRecording();
    } catch (error) {
      _lastError ??= 'Could not finish recording: $error';
    }
    notifyListeners();
  }

  Future<void> submit({required String sessionId}) async {
    final imageBase64 = _capturedImageBase64;
    final audioBase64 = _capturedAudioBase64;

    if (imageBase64 == null || audioBase64 == null) {
      _lastError ??= 'Capture an image and audio before sending.';
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

  Future<void> captureAndLookupCurrency() async {
    _lastError = null;
    _lastResponse = null;
    notifyListeners();

    final String imageBase64;
    try {
      imageBase64 = await _mediaCaptureService.captureImageBase64();
    } catch (error) {
      _lastError = 'Could not access the camera: $error';
      notifyListeners();
      return;
    }

    _isBusy = true;
    notifyListeners();

    try {
      final result = await _backendClient.lookupCurrency(imageBase64);
      _lastResponse = ConversationResponse(
        sessionId: 'money-mode',
        text: result.spokenText,
        audioBase64: result.audioBase64,
        ttsFallbackRequired: result.ttsFallbackRequired,
      );
      _lastError = null;
    } catch (error) {
      _lastError = error.toString();
    } finally {
      _isBusy = false;
      notifyListeners();
    }

    await playLastResponse();
  }

  Future<void> lookupProductByBarcode(String barcode) async {
    _lastError = null;
    _lastResponse = null;
    _isBusy = true;
    notifyListeners();

    try {
      final result = await _backendClient.lookupProduct(barcode);
      final text = result.found ? _describeProduct(result.product!) : "I couldn't find a product for this barcode.";
      _lastResponse = ConversationResponse(
        sessionId: 'barcode-mode',
        text: text,
        audioBase64: '',
        ttsFallbackRequired: true,
      );
      _lastError = null;
    } catch (error) {
      _lastError = error.toString();
    } finally {
      _isBusy = false;
      notifyListeners();
    }

    await playLastResponse();
  }

  String _describeProduct(ProductInfo product) {
    final buffer = StringBuffer('This is ${product.name}');
    if (product.brand != null) {
      buffer.write(' by ${product.brand}');
    }
    buffer.write('.');
    if (product.allergens.isNotEmpty) {
      buffer.write(' Contains: ${product.allergens.join(', ')}.');
    }
    return buffer.toString();
  }

  Future<void> playLastResponse() async {
    final response = _lastResponse;
    if (response == null) {
      return;
    }
    if (response.ttsFallbackRequired) {
      await _osTtsFallbackService.speak(response.text);
    } else {
      await _audioPlaybackService.playBase64Audio(response.audioBase64);
    }
  }

  /// Test-only helper: sets lastResponse directly, bypassing submit(), so
  /// widget tests can verify UI reacts to a completed response without
  /// needing a real or fake network round-trip.
  @visibleForTesting
  void debugSetResponseForTest(String text, {bool ttsFallbackRequired = false}) {
    _lastResponse = ConversationResponse(
      sessionId: 'test-session',
      text: text,
      audioBase64: 'test-audio',
      ttsFallbackRequired: ttsFallbackRequired,
    );
    notifyListeners();
  }
}
