import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:image/image.dart' as img;
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';

abstract class MediaCaptureService {
  Future<String> captureImageBase64();
  Future<void> startAudioRecording();
  Future<String> stopAudioRecording();
}

/// Resizes [rawBytes] so its longest edge is at most [maxDimension], then
/// re-encodes as JPEG at [jpegQuality]. Pure function -- no hardware
/// dependency -- so it can be unit-tested directly, unlike camera capture.
Uint8List compressImageBytes(
  Uint8List rawBytes, {
  int maxDimension = 1024,
  int jpegQuality = 70,
}) {
  final decoded = img.decodeImage(rawBytes);
  if (decoded == null) {
    throw StateError('Image bytes could not be decoded for compression.');
  }

  final resized = decoded.width > decoded.height
      ? img.copyResize(decoded, width: maxDimension >= decoded.width ? decoded.width : maxDimension)
      : img.copyResize(decoded, height: maxDimension >= decoded.height ? decoded.height : maxDimension);

  return Uint8List.fromList(img.encodeJpg(resized, quality: jpegQuality));
}

/// Captures a compressed camera frame (max 1024px longest edge, JPEG ~70)
/// and records microphone audio, both base64-encoded for the backend.
class CameraMediaCaptureService implements MediaCaptureService {
  CameraMediaCaptureService({AudioRecorder? audioRecorder})
      : _audioRecorder = audioRecorder ?? AudioRecorder();

  CameraController? _cameraController;
  final AudioRecorder _audioRecorder;

  Future<CameraController> _ensureCamera() async {
    final existing = _cameraController;
    if (existing != null && existing.value.isInitialized) {
      return existing;
    }
    await Permission.camera.request();
    final cameras = await availableCameras();
    final controller = CameraController(
      cameras.first,
      ResolutionPreset.high,
      enableAudio: false,
    );
    await controller.initialize();
    _cameraController = controller;
    return controller;
  }

  @override
  Future<String> captureImageBase64() async {
    final controller = await _ensureCamera();
    final file = await controller.takePicture();
    final rawBytes = await File(file.path).readAsBytes();
    final compressedBytes = compressImageBytes(rawBytes);
    return base64Encode(compressedBytes);
  }

  @override
  Future<void> startAudioRecording() async {
    await Permission.microphone.request();
    final path = await _recordingPath();
    await _audioRecorder.start(const RecordConfig(), path: path);
  }

  @override
  Future<String> stopAudioRecording() async {
    final path = await _audioRecorder.stop();
    if (path == null) {
      throw StateError('Audio recording did not produce a file.');
    }
    final bytes = await File(path).readAsBytes();
    return base64Encode(bytes);
  }

  Future<String> _recordingPath() async {
    final tempDir = Directory.systemTemp;
    return '${tempDir.path}/be_my_eye_recording_${DateTime.now().millisecondsSinceEpoch}.m4a';
  }
}
