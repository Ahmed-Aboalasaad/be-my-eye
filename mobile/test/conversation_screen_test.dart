import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:be_my_eye/features/conversation/audio_playback.dart';
import 'package:be_my_eye/features/conversation/backend_client.dart';
import 'package:be_my_eye/features/conversation/conversation_screen.dart';
import 'package:be_my_eye/features/conversation/conversation_state.dart';
import 'package:be_my_eye/features/conversation/media_services.dart';
import 'package:be_my_eye/features/conversation/models.dart';
import 'package:be_my_eye/features/conversation/os_tts_fallback.dart';

class _FakeBackendClient extends BackendClient {
  _FakeBackendClient() : super(baseUrl: 'http://localhost');

  @override
  Future<ConversationResponse> sendConversation(ConversationRequest request) async {
    throw UnimplementedError('not exercised in this test');
  }
}

class _FakeMediaCaptureService implements MediaCaptureService {
  @override
  Future<String> captureImageBase64() async => 'image';
  @override
  Future<void> startAudioRecording() async {}
  @override
  Future<String> stopAudioRecording() async => 'audio';
}

class _FakeAudioPlaybackService implements AudioPlaybackService {
  @override
  Future<void> playBase64Audio(String audioBase64) async {}
}

class _FakeOsTtsFallbackService implements OsTtsFallbackService {
  @override
  Future<void> speak(String text) async {}
}

void main() {
  testWidgets('shows the idle hold-to-ask state with a matching semantics label',
      (WidgetTester tester) async {
    final state = ConversationState(
      backendClient: _FakeBackendClient(),
      mediaCaptureService: _FakeMediaCaptureService(),
      audioPlaybackService: _FakeAudioPlaybackService(),
      osTtsFallbackService: _FakeOsTtsFallbackService(),
    );

    await tester.pumpWidget(
      ChangeNotifierProvider<ConversationState>.value(
        value: state,
        child: const MaterialApp(home: ConversationScreen()),
      ),
    );

    expect(find.text('Hold to ask'), findsOneWidget);
    expect(find.bySemanticsLabel('Hold to ask a question'), findsOneWidget);
  });

  testWidgets('shows the response text once a response arrives',
      (WidgetTester tester) async {
    final state = ConversationState(
      backendClient: _FakeBackendClient(),
      mediaCaptureService: _FakeMediaCaptureService(),
      audioPlaybackService: _FakeAudioPlaybackService(),
      osTtsFallbackService: _FakeOsTtsFallbackService(),
    );
    state.loadDemoCapture();

    await tester.pumpWidget(
      ChangeNotifierProvider<ConversationState>.value(
        value: state,
        child: const MaterialApp(home: ConversationScreen()),
      ),
    );

    // Simulate a completed response without exercising the real backend call.
    state.debugSetResponseForTest('assistant reply');
    await tester.pump();

    expect(find.text('assistant reply'), findsOneWidget);
  });
}
