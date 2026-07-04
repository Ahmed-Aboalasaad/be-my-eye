import 'package:flutter_test/flutter_test.dart';

import 'package:be_my_eye/features/conversation/audio_playback.dart';
import 'package:be_my_eye/features/conversation/backend_client.dart';
import 'package:be_my_eye/features/conversation/conversation_state.dart';
import 'package:be_my_eye/features/conversation/media_services.dart';
import 'package:be_my_eye/features/conversation/models.dart';
import 'package:be_my_eye/features/conversation/os_tts_fallback.dart';

class FakeBackendClient extends BackendClient {
  FakeBackendClient() : super(baseUrl: 'http://localhost');

  ConversationRequest? lastRequest;
  String? lastCurrencyImageBase64;
  String? lastBarcode;

  @override
  Future<ConversationResponse> sendConversation(ConversationRequest request) async {
    lastRequest = request;
    return ConversationResponse(
      sessionId: request.sessionId,
      text: 'assistant reply',
      audioBase64: 'response-audio',
    );
  }

  @override
  Future<CurrencyLookupResponse> lookupCurrency(String imageBase64) async {
    lastCurrencyImageBase64 = imageBase64;
    return CurrencyLookupResponse(
      found: true,
      denomination: '20 EGP',
      confidence: 0.92,
      spokenText: 'This looks like 20 EGP.',
      audioBase64: 'currency-audio',
    );
  }

  @override
  Future<ProductLookupResponse> lookupProduct(String barcode) async {
    lastBarcode = barcode;
    if (barcode == '0000000000000') {
      return ProductLookupResponse(found: false, product: null);
    }
    return ProductLookupResponse(
      found: true,
      product: ProductInfo(
        name: 'Sample Product',
        brand: 'Sample Brand',
        allergens: const ['milk'],
      ),
    );
  }
}

class FakeMediaCaptureService implements MediaCaptureService {
  bool captureImageCalled = false;
  bool startAudioRecordingCalled = false;
  bool stopAudioRecordingCalled = false;

  @override
  Future<String> captureImageBase64() async {
    captureImageCalled = true;
    return 'captured-image';
  }

  @override
  Future<void> startAudioRecording() async {
    startAudioRecordingCalled = true;
  }

  @override
  Future<String> stopAudioRecording() async {
    stopAudioRecordingCalled = true;
    return 'captured-audio';
  }
}

class FakeAudioPlaybackService implements AudioPlaybackService {
  String? playedAudioBase64;

  @override
  Future<void> playBase64Audio(String audioBase64) async {
    playedAudioBase64 = audioBase64;
  }
}

class FakeOsTtsFallbackService implements OsTtsFallbackService {
  String? spokenText;

  @override
  Future<void> speak(String text) async {
    spokenText = text;
  }
}

class ThrowingMediaCaptureService implements MediaCaptureService {
  @override
  Future<String> captureImageBase64() async {
    throw StateError('No cameras available.');
  }

  @override
  Future<void> startAudioRecording() async {}

  @override
  Future<String> stopAudioRecording() async {
    throw StateError('Audio recording did not produce a file.');
  }
}

class CameraFailsButMicWorksMediaCaptureService implements MediaCaptureService {
  @override
  Future<String> captureImageBase64() async {
    throw StateError('No cameras available.');
  }

  @override
  Future<void> startAudioRecording() async {}

  @override
  Future<String> stopAudioRecording() async {
    return 'captured-audio';
  }
}

void main() {
  test('ConversationState rejects send attempts without captures', () async {
    final backendClient = FakeBackendClient();
    final state = ConversationState(
      backendClient: backendClient,
      mediaCaptureService: FakeMediaCaptureService(),
      audioPlaybackService: FakeAudioPlaybackService(),
      osTtsFallbackService: FakeOsTtsFallbackService(),
    );

    await state.submit(sessionId: 'session-empty');

    expect(backendClient.lastRequest, isNull);
    expect(state.lastError, 'Capture an image and audio before sending.');
  });

  test('ConversationState loads demo capture and sends the captured payload', () async {
    final backendClient = FakeBackendClient();
    final mediaCaptureService = FakeMediaCaptureService();
    final audioPlaybackService = FakeAudioPlaybackService();
    final state = ConversationState(
      backendClient: backendClient,
      mediaCaptureService: mediaCaptureService,
      audioPlaybackService: audioPlaybackService,
      osTtsFallbackService: FakeOsTtsFallbackService(),
      debug: true,
    );

    state.loadDemoCapture();
    await state.submit(sessionId: 'session-1');

    expect(backendClient.lastRequest?.sessionId, 'session-1');
    expect(backendClient.lastRequest?.debug, isTrue);
    expect(state.lastResponse?.text, 'assistant reply');
    expect(state.lastError, isNull);
  });

  test('ConversationState captures image and audio before sending', () async {
    final backendClient = FakeBackendClient();
    final mediaCaptureService = FakeMediaCaptureService();
    final audioPlaybackService = FakeAudioPlaybackService();
    final state = ConversationState(
      backendClient: backendClient,
      mediaCaptureService: mediaCaptureService,
      audioPlaybackService: audioPlaybackService,
      osTtsFallbackService: FakeOsTtsFallbackService(),
    );

    await state.captureImage();
    await state.startAudioRecording();
    await state.stopAudioRecording();
    await state.submit(sessionId: 'session-2');

    expect(mediaCaptureService.captureImageCalled, isTrue);
    expect(mediaCaptureService.startAudioRecordingCalled, isTrue);
    expect(mediaCaptureService.stopAudioRecordingCalled, isTrue);
    expect(backendClient.lastRequest?.imageBase64, 'captured-image');
    expect(backendClient.lastRequest?.audioBase64, 'captured-audio');
  });

  test('ConversationState can play the last response audio', () async {
    final backendClient = FakeBackendClient();
    final mediaCaptureService = FakeMediaCaptureService();
    final audioPlaybackService = FakeAudioPlaybackService();
    final state = ConversationState(
      backendClient: backendClient,
      mediaCaptureService: mediaCaptureService,
      audioPlaybackService: audioPlaybackService,
      osTtsFallbackService: FakeOsTtsFallbackService(),
    );

    state.loadDemoCapture();
    await state.submit(sessionId: 'session-3');
    await state.playLastResponse();

    expect(audioPlaybackService.playedAudioBase64, 'response-audio');
  });

  test('ConversationState surfaces a specific error when camera capture fails', () async {
    final backendClient = FakeBackendClient();
    final state = ConversationState(
      backendClient: backendClient,
      mediaCaptureService: ThrowingMediaCaptureService(),
      audioPlaybackService: FakeAudioPlaybackService(),
      osTtsFallbackService: FakeOsTtsFallbackService(),
    );

    await state.captureImage();

    expect(state.lastError, contains('Could not access the camera'));
  });

  test('ConversationState surfaces a specific error when stopping the recording fails', () async {
    final backendClient = FakeBackendClient();
    final state = ConversationState(
      backendClient: backendClient,
      mediaCaptureService: ThrowingMediaCaptureService(),
      audioPlaybackService: FakeAudioPlaybackService(),
      osTtsFallbackService: FakeOsTtsFallbackService(),
    );

    await state.stopAudioRecording();

    expect(state.lastError, contains('Could not finish recording'));
  });

  test('a later successful step does not erase an earlier step\'s error', () async {
    final backendClient = FakeBackendClient();
    final state = ConversationState(
      backendClient: backendClient,
      mediaCaptureService: CameraFailsButMicWorksMediaCaptureService(),
      audioPlaybackService: FakeAudioPlaybackService(),
      osTtsFallbackService: FakeOsTtsFallbackService(),
    );

    await state.captureImage();
    await state.startAudioRecording();
    await state.stopAudioRecording();

    expect(state.lastError, contains('Could not access the camera'));
  });

  test('starting a new gesture clears the previous turn\'s answer', () async {
    final backendClient = FakeBackendClient();
    final mediaCaptureService = FakeMediaCaptureService();
    final audioPlaybackService = FakeAudioPlaybackService();
    final state = ConversationState(
      backendClient: backendClient,
      mediaCaptureService: mediaCaptureService,
      audioPlaybackService: audioPlaybackService,
      osTtsFallbackService: FakeOsTtsFallbackService(),
    );

    state.loadDemoCapture();
    await state.submit(sessionId: 'session-turn-1');
    expect(state.lastResponse, isNotNull);

    await state.captureImage();

    expect(state.lastResponse, isNull);
  });

  test('ConversationState speaks locally when tts_fallback_required is true', () async {
    final backendClient = FakeBackendClient();
    final audioPlaybackService = FakeAudioPlaybackService();
    final osTtsFallbackService = FakeOsTtsFallbackService();
    final state = ConversationState(
      backendClient: backendClient,
      mediaCaptureService: FakeMediaCaptureService(),
      audioPlaybackService: audioPlaybackService,
      osTtsFallbackService: osTtsFallbackService,
    );

    state.debugSetResponseForTest('the answer', ttsFallbackRequired: true);
    await state.playLastResponse();

    expect(osTtsFallbackService.spokenText, 'the answer');
    expect(audioPlaybackService.playedAudioBase64, isNull);
  });

  test('ConversationState captures a photo and looks up currency', () async {
    final backendClient = FakeBackendClient();
    final mediaCaptureService = FakeMediaCaptureService();
    final audioPlaybackService = FakeAudioPlaybackService();
    final state = ConversationState(
      backendClient: backendClient,
      mediaCaptureService: mediaCaptureService,
      audioPlaybackService: audioPlaybackService,
      osTtsFallbackService: FakeOsTtsFallbackService(),
    );

    await state.captureAndLookupCurrency();

    expect(mediaCaptureService.captureImageCalled, isTrue);
    expect(backendClient.lastCurrencyImageBase64, 'captured-image');
    expect(state.lastResponse?.text, 'This looks like 20 EGP.');
    expect(audioPlaybackService.playedAudioBase64, 'currency-audio');
  });

  test('ConversationState looks up a product by barcode and describes it', () async {
    final backendClient = FakeBackendClient();
    final state = ConversationState(
      backendClient: backendClient,
      mediaCaptureService: FakeMediaCaptureService(),
      audioPlaybackService: FakeAudioPlaybackService(),
      osTtsFallbackService: FakeOsTtsFallbackService(),
    );

    await state.lookupProductByBarcode('1234567890123');

    expect(backendClient.lastBarcode, '1234567890123');
    expect(state.lastResponse?.text, contains('Sample Product'));
    expect(state.lastResponse?.text, contains('milk'));
    expect(state.lastResponse?.ttsFallbackRequired, isTrue);
  });

  test('ConversationState reports when a barcode is not found', () async {
    final backendClient = FakeBackendClient();
    final state = ConversationState(
      backendClient: backendClient,
      mediaCaptureService: FakeMediaCaptureService(),
      audioPlaybackService: FakeAudioPlaybackService(),
      osTtsFallbackService: FakeOsTtsFallbackService(),
    );

    await state.lookupProductByBarcode('0000000000000');

    expect(state.lastResponse?.text, contains("couldn't find"));
  });
}
