import 'package:flutter_test/flutter_test.dart';

import 'package:be_my_eye/features/conversation/audio_playback.dart';
import 'package:be_my_eye/features/conversation/backend_client.dart';
import 'package:be_my_eye/features/conversation/conversation_state.dart';
import 'package:be_my_eye/features/conversation/media_services.dart';
import 'package:be_my_eye/features/conversation/models.dart';

class FakeBackendClient extends BackendClient {
  FakeBackendClient() : super(baseUrl: 'http://localhost');

  ConversationRequest? lastRequest;

  @override
  Future<ConversationResponse> sendConversation(ConversationRequest request) async {
    lastRequest = request;
    return ConversationResponse(
      sessionId: request.sessionId,
      text: 'assistant reply',
      audioBase64: 'response-audio',
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

void main() {
  test('ConversationState rejects send attempts without captures', () async {
    final backendClient = FakeBackendClient();
    final state = ConversationState(
      backendClient: backendClient,
      mediaCaptureService: FakeMediaCaptureService(),
      audioPlaybackService: FakeAudioPlaybackService(),
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
    );

    await state.stopAudioRecording();

    expect(state.lastError, contains('Could not finish recording'));
  });
}
