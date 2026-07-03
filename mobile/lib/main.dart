import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'features/conversation/audio_playback.dart';
import 'features/conversation/backend_client.dart';
import 'features/conversation/conversation_screen.dart';
import 'features/conversation/conversation_state.dart';
import 'features/conversation/media_services.dart';
import 'features/conversation/os_tts_fallback.dart';

const String _backendUrl = String.fromEnvironment(
  'BACKEND_URL',
  defaultValue: 'https://backend-mu-azure-ghm6imsjg1.vercel.app',
);

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider<ConversationState>(
      create: (_) => ConversationState(
        backendClient: BackendClient(baseUrl: _backendUrl),
        mediaCaptureService: CameraMediaCaptureService(),
        audioPlaybackService: JustAudioPlaybackService(),
        osTtsFallbackService: FlutterOsTtsFallbackService(),
      ),
      child: MaterialApp(
        title: 'Be My Eye',
        theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
        home: const ConversationScreen(),
      ),
    );
  }
}
