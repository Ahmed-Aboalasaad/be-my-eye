import 'package:camera/camera.dart';
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
  final List<ConversationTurn> _history = [];

  String? get lastError => _lastError;
  ConversationResponse? get lastResponse => _lastResponse;
  bool get isBusy => _isBusy;
  List<ConversationTurn> get history => List.unmodifiable(_history);
  CameraController? get cameraPreviewController => _mediaCaptureService.cameraController;

  void loadDemoCapture() {
    _capturedImageBase64 = DemoCapture.imageBase64();
    _capturedAudioBase64 = DemoCapture.audioBase64();
    notifyListeners();
  }

  /// Warms up the camera as soon as the screen loads (rather than waiting
  /// for the first hold-to-ask gesture) so a live preview can be shown as
  /// the screen's background right away.
  Future<void> initializeCameraPreview() async {
    await _mediaCaptureService.ensureCameraReady();
    notifyListeners();
  }

  /// Releases the camera while the app is backgrounded so it doesn't sit
  /// locked (draining battery, blocking other apps) until the app is fully
  /// terminated. Call [initializeCameraPreview] again on resume.
  Future<void> disposeCameraPreview() async {
    await _mediaCaptureService.disposeCamera();
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

  /// Every failure branch in this file must go through here rather than
  /// setting `_lastResponse = null` on error: this is a voice-first app, so
  /// leaving `_lastResponse` null on failure means playLastResponse() has
  /// nothing to speak and the user hears total silence with no way to know
  /// what happened. `spokenMessage` is what the user hears (Egyptian
  /// Arabic, via the on-device fallback voice since there's no cloud audio
  /// for a locally-detected failure); `technicalDetail` stays in
  /// `_lastError` for the on-screen/debug text only.
  void _failWith({required String sessionId, required String spokenMessage, required String technicalDetail}) {
    _lastError = technicalDetail;
    _lastResponse = ConversationResponse(
      sessionId: sessionId,
      text: spokenMessage,
      audioBase64: '',
      ttsFallbackRequired: true,
    );
  }

  Future<void> submit({required String sessionId}) async {
    final imageBase64 = _capturedImageBase64;
    final audioBase64 = _capturedAudioBase64;

    if (_lastError != null || imageBase64 == null || audioBase64 == null) {
      _failWith(
        sessionId: sessionId,
        spokenMessage: 'معلش، حصلت مشكلة وأنا بحاول أسمعك أو أصورك. جرب تاني.',
        technicalDetail: _lastError ?? 'Capture an image and audio before sending.',
      );
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
          history: List.unmodifiable(_history),
        ),
      );
      _lastResponse = response;
      _lastError = null;
      if (response.transcript.isNotEmpty) {
        _history.add(ConversationTurn(userText: response.transcript, assistantText: response.text));
      }
    } catch (error) {
      _failWith(
        sessionId: sessionId,
        spokenMessage: 'معلش، حصلت مشكلة وأنا بحاول أجاوبك. جرب تاني.',
        technicalDetail: error.toString(),
      );
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
      _failWith(
        sessionId: 'money-mode',
        spokenMessage: 'معلش، مش قادر أوصل للكاميرا. جرب تاني.',
        technicalDetail: 'Could not access the camera: $error',
      );
      notifyListeners();
      await playLastResponse();
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
      _failWith(
        sessionId: 'money-mode',
        spokenMessage: 'معلش، حصلت مشكلة وأنا بحاول أعرف الفئة. جرب تاني.',
        technicalDetail: error.toString(),
      );
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
      final text = result.found ? _describeProduct(result.product!) : "مقدرتش ألاقي منتج للباركود ده.";
      _lastResponse = ConversationResponse(
        sessionId: 'barcode-mode',
        text: text,
        audioBase64: '',
        ttsFallbackRequired: true,
      );
      _lastError = null;
    } catch (error) {
      _failWith(
        sessionId: 'barcode-mode',
        spokenMessage: 'معلش، حصلت مشكلة وأنا بدور على المنتج ده. جرب تاني.',
        technicalDetail: error.toString(),
      );
    } finally {
      _isBusy = false;
      notifyListeners();
    }

    await playLastResponse();
  }

  String _describeProduct(ProductInfo product) {
    final buffer = StringBuffer('المنتج ده اسمه ${product.name}');
    if (product.brand != null) {
      buffer.write(' من ${product.brand}');
    }
    buffer.write('.');
    if (product.allergens.isNotEmpty) {
      buffer.write(' وبيحتوي على: ${product.allergens.join(', ')}.');
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
      return;
    }
    try {
      await _audioPlaybackService.playBase64Audio(response.audioBase64);
    } catch (_) {
      // The backend said audio was ready, but playback failed anyway (e.g.
      // empty/corrupt audio bytes slipped through). Never let the user end
      // up with visible text and total silence -- fall back to speaking it
      // locally instead of just swallowing the error.
      await _osTtsFallbackService.speak(response.text);
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

  @override
  void dispose() {
    // ChangeNotifier.dispose() is synchronous, so this is fire-and-forget --
    // the camera hardware still gets released, just not necessarily before
    // this call returns. Without this, the camera controller added for the
    // live preview background was never released at all.
    _mediaCaptureService.disposeCamera();
    super.dispose();
  }
}
