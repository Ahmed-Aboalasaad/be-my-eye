import 'dart:convert';
import 'dart:io';

import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';

abstract class AudioPlaybackService {
  Future<void> playBase64Audio(String audioBase64);
}

/// Decodes base64 audio to a temp file and plays it through the device
/// speaker via just_audio.
class JustAudioPlaybackService implements AudioPlaybackService {
  JustAudioPlaybackService({AudioPlayer? player}) : _player = player ?? AudioPlayer();

  final AudioPlayer _player;

  @override
  Future<void> playBase64Audio(String audioBase64) async {
    final bytes = base64Decode(audioBase64);
    final tempDir = await getTemporaryDirectory();
    final file = File(
      '${tempDir.path}/be_my_eye_response_${DateTime.now().millisecondsSinceEpoch}.wav',
    );
    await file.writeAsBytes(bytes);
    await _player.setFilePath(file.path);
    await _player.play();
  }
}
