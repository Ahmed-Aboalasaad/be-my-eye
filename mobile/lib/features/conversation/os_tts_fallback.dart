import 'package:flutter_tts/flutter_tts.dart';

/// Speaks text using the phone's built-in offline Arabic voice. Used when
/// cloud Egyptian TTS synthesis failed (ConversationResponse.ttsFallbackRequired)
/// so the user always hears an answer, even without a natural Egyptian accent.
abstract class OsTtsFallbackService {
  Future<void> speak(String text);
}

class FlutterOsTtsFallbackService implements OsTtsFallbackService {
  FlutterOsTtsFallbackService({FlutterTts? tts}) : _tts = tts ?? FlutterTts() {
    // 'ar-EG' requests the Egyptian locale specifically rather than a
    // generic/MSA Arabic voice, so the fallback voice doesn't sound like an
    // abrupt switch away from the cloud Egyptian TTS voice.
    _tts.setLanguage('ar-EG');
  }

  final FlutterTts _tts;

  @override
  Future<void> speak(String text) async {
    await _tts.speak(text);
  }
}
