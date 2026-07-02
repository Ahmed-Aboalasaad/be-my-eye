import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:be_my_eye/features/conversation/backend_client.dart';
import 'package:be_my_eye/features/conversation/models.dart';

void main() {
  test('sendConversation posts JSON to {baseUrl}/conversation and parses the response', () async {
    http.Request? capturedRequest;

    final mockClient = MockClient((request) async {
      capturedRequest = request;
      return http.Response(
        jsonEncode({
          'session_id': 'session-1',
          'text': 'assistant reply',
          'audio_base64': 'abcd',
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final client = BackendClient(baseUrl: 'https://example.com', httpClient: mockClient);

    final response = await client.sendConversation(
      ConversationRequest(
        sessionId: 'session-1',
        imageBase64: 'image',
        audioBase64: 'audio',
        debug: false,
      ),
    );

    expect(capturedRequest?.url.toString(), 'https://example.com/conversation');
    expect(capturedRequest?.method, 'POST');
    expect(
      jsonDecode(capturedRequest!.body),
      {
        'session_id': 'session-1',
        'image_base64': 'image',
        'audio_base64': 'audio',
        'debug': false,
      },
    );
    expect(response.text, 'assistant reply');
    expect(response.audioBase64, 'abcd');
  });

  test('sendConversation throws BackendException on a non-200 response', () async {
    final mockClient = MockClient((request) async => http.Response('server error', 500));
    final client = BackendClient(baseUrl: 'https://example.com', httpClient: mockClient);

    expect(
      () => client.sendConversation(
        ConversationRequest(sessionId: 's', imageBase64: 'i', audioBase64: 'a'),
      ),
      throwsA(isA<BackendException>()),
    );
  });
}
