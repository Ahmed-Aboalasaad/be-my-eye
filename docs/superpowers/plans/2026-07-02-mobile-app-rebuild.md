# Mobile App Rebuild (Flutter) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `mobile/lib/` from scratch so the Flutter app compiles, all committed tests in `mobile/test/` pass, the app talks to the live Vercel backend, and users interact through a single accessible "hold to ask" screen.

**Architecture:** A thin `features/conversation/` module: data models with backend-matching JSON keys, a `BackendClient` wrapping one HTTP POST, two hardware-facing service interfaces (media capture, audio playback) each with a real implementation, a `ConversationState` orchestrator (`ChangeNotifier`) that drives capture → submit → playback, and one `conversation_screen.dart` UI consuming that state via `provider`. No new architecture beyond what the already-committed tests in `mobile/test/` dictate.

**Tech Stack:** Flutter (Dart SDK ≥3.8.0), `http`, `just_audio`, `camera`, `record`, `path_provider`, `permission_handler`, `image` (new — for capture-side compression), `provider` (new — for state injection).

## Global Constraints

- Dart SDK `>=3.8.0 <4.0.0` (from `mobile/pubspec.yaml`).
- Backend base URL is injected via `--dart-define=BACKEND_URL=...`; never hardcode the production URL in source. Production URL: `https://backend-mu-azure-ghm6imsjg1.vercel.app`.
- Image capture must be compressed before sending: max ~1024px on the longest edge, JPEG quality ~70 (Vercel's ~4.5MB request body limit; base64 inflates payload ~33%).
- Client-carried conversation history is **not** in scope for this plan (a later plan adds it to the backend and wires it here).
- Every JSON key in requests/responses must exactly match the backend contract already defined in `backend/app/schemas/`: `session_id`, `image_base64`, `audio_base64`, `debug`, `text`, `transcript`, `selected_providers`, `vision_summary`, `ocr_text`.
- Hardware-facing code (camera, microphone, audio playback) cannot be meaningfully unit-tested in `flutter test` (no camera/mic in a headless test runner) — those tasks are verified via `flutter analyze` (static/compile correctness) instead of a fake assertion. Do not write a test that doesn't actually exercise real behavior just to have a test file.
- One commit per logical file change; TDD test-then-implementation pairs commit together (test + minimal implementation is one atomic cycle — see Plan 1's precedent).

---

## Task 1: Add `provider` and `image` packages to `pubspec.yaml`

**Files:**
- Modify: `mobile/pubspec.yaml`

**Interfaces:**
- Consumes: nothing.
- Produces: `provider` package (state injection, used by Task 8's `conversation_screen.dart`) and `image` package (capture-side compression, used by Task 5's real `MediaCaptureService`) available to later tasks.

- [ ] **Step 1: Add the two new dependencies**

In `mobile/pubspec.yaml`, under the existing `dependencies:` block (after `permission_handler: ^12.0.3`), add:

```yaml
  provider: ^6.1.2
  image: ^4.3.0
```

The full `dependencies:` block should read:

```yaml
dependencies:
  flutter:
    sdk: flutter
  image_picker: ^1.2.2
  http: ^1.2.2
  just_audio: ^0.10.6
  path_provider: ^2.1.6
  record: ^7.1.1
  camera: ^0.12.0+1
  permission_handler: ^12.0.3
  provider: ^6.1.2
  image: ^4.3.0
```

- [ ] **Step 2: Verify the file is valid YAML and Flutter can resolve it**

Run: `cd mobile && flutter pub get`
Expected: completes without error, prints a summary of resolved packages including `provider` and `image`.

- [ ] **Step 3: Commit**

```bash
git add mobile/pubspec.yaml mobile/pubspec.lock
git commit -m "$(cat <<'EOF'
build(mobile): add provider and image packages

provider will inject ConversationState into the widget tree
(conversation_screen.dart); image will handle capture-side
compression (max ~1024px, JPEG ~70) before frames are sent to the
backend, staying under Vercel's request payload limit.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `models.dart` — request/response data classes

**Files:**
- Create: `mobile/lib/features/conversation/models.dart`
- Test: `mobile/test/models_test.dart` (already exists — do not modify; make it pass)

**Interfaces:**
- Consumes: nothing.
- Produces: `ConversationRequest({required String sessionId, required String imageBase64, required String audioBase64, bool debug = false})` with `.toJson()`; `ConversationResponse` with fields `sessionId`, `text`, `audioBase64`, `debug` (nullable `ConversationDebug`) and `ConversationResponse.fromJson(Map<String, dynamic>)`; `ConversationDebug` with fields `transcript`, `selectedProviders` (`List<String>`), `visionSummary` (nullable), `ocrText` (nullable). Consumed by `backend_client.dart` (Task 3), `conversation_state.dart` (Task 7), and the already-existing `conversation_state_test.dart`.

**Context:** `mobile/test/models_test.dart` already exists and defines the exact contract — read it before starting:

```dart
import 'package:flutter_test/flutter_test.dart';

import 'package:be_my_eye/features/conversation/models.dart';

void main() {
  test('ConversationRequest serializes to backend payload keys', () {
    final request = ConversationRequest(
      sessionId: 'session-1',
      imageBase64: 'image',
      audioBase64: 'audio',
      debug: true,
    );

    expect(request.toJson(), {
      'session_id': 'session-1',
      'image_base64': 'image',
      'audio_base64': 'audio',
      'debug': true,
    });
  });

  test('ConversationResponse parses backend response shape', () {
    final response = ConversationResponse.fromJson({
      'session_id': 'session-1',
      'text': 'hello',
      'audio_base64': 'abcd',
      'debug': {
        'transcript': 'what is this',
        'selected_providers': ['vision'],
        'vision_summary': 'a desk',
        'ocr_text': null,
      },
    });

    expect(response.sessionId, 'session-1');
    expect(response.text, 'hello');
    expect(response.audioBase64, 'abcd');
    expect(response.debug?.selectedProviders, ['vision']);
  });
}
```

- [ ] **Step 1: Confirm the test currently fails (no implementation exists yet)**

Run: `cd mobile && flutter test test/models_test.dart`
Expected: FAIL — `Error: Error when reading 'lib/features/conversation/models.dart': No such file or directory` (or an unresolved-import error), since `mobile/lib/` does not exist yet.

- [ ] **Step 2: Write `mobile/lib/features/conversation/models.dart`**

```dart
class ConversationRequest {
  ConversationRequest({
    required this.sessionId,
    required this.imageBase64,
    required this.audioBase64,
    this.debug = false,
  });

  final String sessionId;
  final String imageBase64;
  final String audioBase64;
  final bool debug;

  Map<String, dynamic> toJson() => {
        'session_id': sessionId,
        'image_base64': imageBase64,
        'audio_base64': audioBase64,
        'debug': debug,
      };
}

class ConversationDebug {
  ConversationDebug({
    required this.transcript,
    required this.selectedProviders,
    this.visionSummary,
    this.ocrText,
  });

  final String transcript;
  final List<String> selectedProviders;
  final String? visionSummary;
  final String? ocrText;

  factory ConversationDebug.fromJson(Map<String, dynamic> json) {
    return ConversationDebug(
      transcript: json['transcript'] as String,
      selectedProviders: List<String>.from(json['selected_providers'] as List),
      visionSummary: json['vision_summary'] as String?,
      ocrText: json['ocr_text'] as String?,
    );
  }
}

class ConversationResponse {
  ConversationResponse({
    required this.sessionId,
    required this.text,
    required this.audioBase64,
    this.debug,
  });

  final String sessionId;
  final String text;
  final String audioBase64;
  final ConversationDebug? debug;

  factory ConversationResponse.fromJson(Map<String, dynamic> json) {
    return ConversationResponse(
      sessionId: json['session_id'] as String,
      text: json['text'] as String,
      audioBase64: json['audio_base64'] as String,
      debug: json['debug'] != null
          ? ConversationDebug.fromJson(json['debug'] as Map<String, dynamic>)
          : null,
    );
  }
}
```

- [ ] **Step 3: Run the test to verify it passes**

Run: `cd mobile && flutter test test/models_test.dart`
Expected: PASS — 2/2 tests.

- [ ] **Step 4: Commit**

```bash
git add mobile/lib/features/conversation/models.dart
git commit -m "$(cat <<'EOF'
feat(mobile): add ConversationRequest/Response/Debug models

Matches the backend's snake_case JSON contract exactly
(backend/app/schemas/common.py, conversation.py). Verified against
the already-committed mobile/test/models_test.dart.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `demo_capture.dart` — embedded demo image/audio for hardware-free testing

**Files:**
- Create: `mobile/lib/features/conversation/demo_capture.dart`
- Test: `mobile/test/demo_capture_test.dart` (already exists — do not modify; make it pass)

**Interfaces:**
- Consumes: nothing.
- Produces: `DemoCapture.imageBase64()` and `DemoCapture.audioBase64()` (static methods returning `String`), consumed by `conversation_state.dart`'s `loadDemoCapture()` (Task 7) and the already-existing `conversation_state_test.dart`.

**Context:** `mobile/test/demo_capture_test.dart` already exists:

```dart
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';

import 'package:be_my_eye/features/conversation/demo_capture.dart';

void main() {
  test('demo capture image is base64 encoded PNG', () {
    final imageBytes = base64Decode(DemoCapture.imageBase64());

    expect(imageBytes.sublist(0, 8), [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);
  });

  test('demo capture audio is a WAV file', () {
    final audioBytes = base64Decode(DemoCapture.audioBase64());

    expect(String.fromCharCodes(audioBytes.sublist(0, 4)), 'RIFF');
    expect(String.fromCharCodes(audioBytes.sublist(8, 12)), 'WAVE');
  });
}
```

The base64 strings below are real, valid, pre-generated assets (a 2x2 white PNG and a ~5ms silent 16kHz mono WAV) — use them verbatim, do not generate new ones.

- [ ] **Step 1: Confirm the test currently fails**

Run: `cd mobile && flutter test test/demo_capture_test.dart`
Expected: FAIL — unresolved import, `demo_capture.dart` does not exist yet.

- [ ] **Step 2: Write `mobile/lib/features/conversation/demo_capture.dart`**

```dart
class DemoCapture {
  static String imageBase64() => _imagePng;

  static String audioBase64() => _audioWav;

  static const String _imagePng =
      'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAE0lEQVR4nGP8//8/AwMDEwMYAAAkBgMBXaJOiAAAAABJRU5ErkJggg==';

  static const String _audioWav =
      'UklGRsQAAABXQVZFZm10IBAAAAABAAEAgD4AAAB9AAACABAAZGF0YaAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';
}
```

- [ ] **Step 3: Run the test to verify it passes**

Run: `cd mobile && flutter test test/demo_capture_test.dart`
Expected: PASS — 2/2 tests.

- [ ] **Step 4: Commit**

```bash
git add mobile/lib/features/conversation/demo_capture.dart
git commit -m "$(cat <<'EOF'
feat(mobile): add DemoCapture with embedded demo image/audio

Real, valid PNG (2x2 white) and WAV (silent, 16kHz mono) assets
embedded as base64 constants, letting ConversationState be exercised
end-to-end without camera/microphone hardware. Verified against the
already-committed mobile/test/demo_capture_test.dart.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `backend_client.dart` — HTTP client wrapping `POST /conversation`

**Files:**
- Create: `mobile/lib/features/conversation/backend_client.dart`
- Test: `mobile/test/backend_client_test.dart` (new — no committed test exists for this file's real HTTP behavior; `conversation_state_test.dart` only exercises it through a `FakeBackendClient` subclass, which doesn't cover the real HTTP request-building logic)

**Interfaces:**
- Consumes: `ConversationRequest`/`ConversationResponse` from `models.dart` (Task 2).
- Produces: `class BackendClient { BackendClient({required String baseUrl}); Future<ConversationResponse> sendConversation(ConversationRequest request); }` — a concrete, non-final class whose `sendConversation` method can be overridden (already relied upon by `mobile/test/conversation_state_test.dart`'s `FakeBackendClient extends BackendClient`). Consumed by `conversation_state.dart` (Task 7) and `main.dart` (Task 9).

- [ ] **Step 1: Write the failing test**

Create `mobile/test/backend_client_test.dart`:

```dart
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
      capturedRequest = request as http.Request;
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile && flutter test test/backend_client_test.dart`
Expected: FAIL — `backend_client.dart` does not exist yet (unresolved import).

- [ ] **Step 3: Write `mobile/lib/features/conversation/backend_client.dart`**

```dart
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

class BackendException implements Exception {
  BackendException(this.message);

  final String message;

  @override
  String toString() => 'BackendException: $message';
}

class BackendClient {
  BackendClient({required this.baseUrl, http.Client? httpClient})
      : _httpClient = httpClient ?? http.Client();

  final String baseUrl;
  final http.Client _httpClient;

  Future<ConversationResponse> sendConversation(ConversationRequest request) async {
    final uri = Uri.parse('$baseUrl/conversation');
    final response = await _httpClient.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(request.toJson()),
    );

    if (response.statusCode != 200) {
      throw BackendException(
        'Backend returned ${response.statusCode}: ${response.body}',
      );
    }

    return ConversationResponse.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mobile && flutter test test/backend_client_test.dart`
Expected: PASS — 2/2 tests.

- [ ] **Step 5: Run the full mobile test suite so far to confirm no regressions**

Run: `cd mobile && flutter test`
Expected: `models_test.dart` and `demo_capture_test.dart` still pass; `backend_client_test.dart` passes; `conversation_state_test.dart` and `widget_test.dart` still fail (their dependencies don't exist yet — expected at this point in the plan).

- [ ] **Step 6: Commit**

```bash
git add mobile/test/backend_client_test.dart mobile/lib/features/conversation/backend_client.dart
git commit -m "$(cat <<'EOF'
feat(mobile): add BackendClient wrapping POST /conversation

Concrete, overridable class (mobile/test/conversation_state_test.dart
already subclasses it as FakeBackendClient) with an injectable
http.Client for testing. Throws BackendException on non-200
responses instead of letting a parse error surface confusingly.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `media_services.dart` — capture interface + real camera/mic implementation

**Files:**
- Create: `mobile/lib/features/conversation/media_services.dart`
- Test: `mobile/test/media_services_test.dart` (new — covers the pure compression function only; the hardware-facing capture/recording methods are verified via `flutter analyze`, per the Global Constraints note on hardware-facing code)

**Interfaces:**
- Consumes: nothing new.
- Produces: `abstract class MediaCaptureService { Future<String> captureImageBase64(); Future<void> startAudioRecording(); Future<String> stopAudioRecording(); }` (already relied upon by `mobile/test/conversation_state_test.dart`'s `FakeMediaCaptureService implements MediaCaptureService`) plus a real implementation `CameraMediaCaptureService implements MediaCaptureService`, and a standalone, unit-testable top-level function `Uint8List compressImageBytes(Uint8List rawBytes, {int maxDimension = 1024, int jpegQuality = 70})`. Consumed by `conversation_state.dart` (Task 7) and `main.dart` (Task 9).

**Context:** The camera/microphone-facing methods (`captureImageBase64`'s camera access, `startAudioRecording`, `stopAudioRecording`) cannot be exercised by `flutter test` (no camera/microphone in a headless test runner) — those are verified via `flutter analyze` only. But the **compression logic itself** is pure bytes-in/bytes-out and needs no hardware, so it's extracted into a standalone `compressImageBytes` function with a real unit test, rather than folding untestable and testable logic together and skipping testing altogether.

- [ ] **Step 1: Write the failing test for the pure compression function**

Create `mobile/test/media_services_test.dart`:

```dart
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;

import 'package:be_my_eye/features/conversation/media_services.dart';

void main() {
  test('compressImageBytes resizes a large image down to the max dimension', () {
    final large = img.Image(width: 2000, height: 1000);
    final rawBytes = Uint8List.fromList(img.encodePng(large));

    final compressed = compressImageBytes(rawBytes, maxDimension: 1024, jpegQuality: 70);

    final decoded = img.decodeImage(compressed);
    expect(decoded, isNotNull);
    expect(decoded!.width, 1024);
    expect(decoded.height, 512);
  });

  test('compressImageBytes leaves a small image at its original size', () {
    final small = img.Image(width: 200, height: 100);
    final rawBytes = Uint8List.fromList(img.encodePng(small));

    final compressed = compressImageBytes(rawBytes, maxDimension: 1024, jpegQuality: 70);

    final decoded = img.decodeImage(compressed);
    expect(decoded!.width, 200);
    expect(decoded.height, 100);
  });

  test('compressImageBytes encodes output as JPEG', () {
    final image = img.Image(width: 100, height: 100);
    final rawBytes = Uint8List.fromList(img.encodePng(image));

    final compressed = compressImageBytes(rawBytes);

    // JPEG magic bytes: 0xFF 0xD8
    expect(compressed[0], 0xFF);
    expect(compressed[1], 0xD8);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile && flutter test test/media_services_test.dart`
Expected: FAIL — `media_services.dart` does not exist yet.

- [ ] **Step 3: Write `mobile/lib/features/conversation/media_services.dart`**

```dart
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mobile && flutter test test/media_services_test.dart`
Expected: PASS — 3/3 tests.

- [ ] **Step 5: Verify the hardware-facing parts with static analysis**

Run: `cd mobile && flutter analyze lib/features/conversation/media_services.dart`
Expected: `No issues found!`

- [ ] **Step 6: Commit**

```bash
git add mobile/lib/features/conversation/media_services.dart mobile/test/media_services_test.dart
git commit -m "$(cat <<'EOF'
feat(mobile): add MediaCaptureService with a unit-tested compression function

Extracts compressImageBytes as a standalone, pure bytes-in/bytes-out
function (no hardware dependency) so the max-1024px/JPEG-~70
compression policy has a real unit test, rather than folding it into
untestable camera-capture code and skipping testing altogether. The
camera/microphone-facing methods on CameraMediaCaptureService still
can't be exercised by flutter test in a headless runner -- verified
via flutter analyze, with behavioral coverage at the consumer level
via the already-committed conversation_state_test.dart's
FakeMediaCaptureService.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `audio_playback.dart` — playback interface + real implementation

**Files:**
- Create: `mobile/lib/features/conversation/audio_playback.dart`

**Interfaces:**
- Consumes: nothing new.
- Produces: `abstract class AudioPlaybackService { Future<void> playBase64Audio(String audioBase64); }` (already relied upon by `mobile/test/conversation_state_test.dart`'s `FakeAudioPlaybackService implements AudioPlaybackService`) plus a real implementation `JustAudioPlaybackService implements AudioPlaybackService`. Consumed by `conversation_state.dart` (Task 7) and `main.dart` (Task 9).

**Context:** Same testing scope note as Task 5 — real audio playback needs a device audio subsystem not available in `flutter test`; verified via `flutter analyze`.

- [ ] **Step 1: Write `mobile/lib/features/conversation/audio_playback.dart`**

```dart
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
```

- [ ] **Step 2: Verify with static analysis**

Run: `cd mobile && flutter analyze lib/features/conversation/audio_playback.dart`
Expected: `No issues found!`

- [ ] **Step 3: Commit**

```bash
git add mobile/lib/features/conversation/audio_playback.dart
git commit -m "$(cat <<'EOF'
feat(mobile): add AudioPlaybackService interface + just_audio implementation

Same testing-scope note as media_services.dart: real device audio
playback can't be exercised by flutter test in a headless runner --
verified via flutter analyze, with behavioral coverage at the
consumer level via the already-committed conversation_state_test.dart's
FakeAudioPlaybackService.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: `conversation_state.dart` — the orchestrator

**Files:**
- Create: `mobile/lib/features/conversation/conversation_state.dart`
- Test: `mobile/test/conversation_state_test.dart` (already exists — do not modify; make it pass)

**Interfaces:**
- Consumes: `BackendClient` (Task 4), `MediaCaptureService` (Task 5), `AudioPlaybackService` (Task 6), `ConversationRequest`/`ConversationResponse` (Task 2), `DemoCapture` (Task 3).
- Produces: `class ConversationState extends ChangeNotifier` with constructor `ConversationState({required BackendClient backendClient, required MediaCaptureService mediaCaptureService, required AudioPlaybackService audioPlaybackService, bool debug = false})`; methods `loadDemoCapture()`, `Future<void> captureImage()`, `Future<void> startAudioRecording()`, `Future<void> stopAudioRecording()`, `Future<void> submit({required String sessionId})`, `Future<void> playLastResponse()`; getters `String? lastError`, `ConversationResponse? lastResponse`, `bool isBusy`. Consumed by `conversation_screen.dart` (Task 8) and `main.dart` (Task 9).

**Context:** `mobile/test/conversation_state_test.dart` already exists in full (read it before starting — it defines `FakeBackendClient`, `FakeMediaCaptureService`, `FakeAudioPlaybackService` and four behavioral tests: rejecting a send with no captures and the exact error string `'Capture an image and audio before sending.'`; loading a demo capture then submitting sends that payload with `debug: true` propagated and populates `lastResponse`; capturing image + recording audio populates the request with the captured values; and `playLastResponse()` forwards `lastResponse!.audioBase64` to the playback service).

- [ ] **Step 1: Confirm the test currently fails**

Run: `cd mobile && flutter test test/conversation_state_test.dart`
Expected: FAIL — `conversation_state.dart` does not exist yet (unresolved import).

- [ ] **Step 2: Write `mobile/lib/features/conversation/conversation_state.dart`**

```dart
import 'package:flutter/foundation.dart';

import 'audio_playback.dart';
import 'backend_client.dart';
import 'demo_capture.dart';
import 'media_services.dart';
import 'models.dart';

class ConversationState extends ChangeNotifier {
  ConversationState({
    required BackendClient backendClient,
    required MediaCaptureService mediaCaptureService,
    required AudioPlaybackService audioPlaybackService,
    this.debug = false,
  })  : _backendClient = backendClient,
        _mediaCaptureService = mediaCaptureService,
        _audioPlaybackService = audioPlaybackService;

  final BackendClient _backendClient;
  final MediaCaptureService _mediaCaptureService;
  final AudioPlaybackService _audioPlaybackService;
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

  Future<void> captureImage() async {
    _capturedImageBase64 = await _mediaCaptureService.captureImageBase64();
    notifyListeners();
  }

  Future<void> startAudioRecording() async {
    await _mediaCaptureService.startAudioRecording();
  }

  Future<void> stopAudioRecording() async {
    _capturedAudioBase64 = await _mediaCaptureService.stopAudioRecording();
    notifyListeners();
  }

  Future<void> submit({required String sessionId}) async {
    final imageBase64 = _capturedImageBase64;
    final audioBase64 = _capturedAudioBase64;

    if (imageBase64 == null || audioBase64 == null) {
      _lastError = 'Capture an image and audio before sending.';
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

  Future<void> playLastResponse() async {
    final response = _lastResponse;
    if (response == null) {
      return;
    }
    await _audioPlaybackService.playBase64Audio(response.audioBase64);
  }
}
```

- [ ] **Step 3: Run the test to verify it passes**

Run: `cd mobile && flutter test test/conversation_state_test.dart`
Expected: PASS — 4/4 tests.

- [ ] **Step 4: Run the full mobile test suite so far**

Run: `cd mobile && flutter test test/models_test.dart test/demo_capture_test.dart test/backend_client_test.dart test/conversation_state_test.dart`
Expected: all pass (only `widget_test.dart`, addressed in Task 9, remains stale/failing at this point).

- [ ] **Step 5: Commit**

```bash
git add mobile/lib/features/conversation/conversation_state.dart
git commit -m "$(cat <<'EOF'
feat(mobile): add ConversationState orchestrator

Drives capture -> submit -> playback: rejects submit without both
captures, loads the demo capture for hardware-free testing, tracks
lastResponse/lastError/isBusy, and extends ChangeNotifier for
Provider-based UI reactivity. Verified against the already-committed
mobile/test/conversation_state_test.dart (4/4 passing).

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: `conversation_screen.dart` — the accessible hold-to-ask screen

**Files:**
- Create: `mobile/lib/features/conversation/conversation_screen.dart`
- Test: `mobile/test/conversation_screen_test.dart` (new)

**Interfaces:**
- Consumes: `ConversationState` (Task 7), via the `provider` package.
- Produces: `class ConversationScreen extends StatelessWidget` — the entire visible screen. Consumed by `main.dart` (Task 9).

**Context:** Per the approved design (spec section 4.5): the whole screen is one press-and-hold gesture target — no per-feature buttons, no small controls to aim at. Holding starts capture (image + audio recording); releasing stops the recording and submits. State is communicated through large text plus a `Semantics` label so a screen reader announces "Listening", "Thinking", or the response — this is the one part of the UI a blind user actually depends on, so the semantic label must always match the visible state text.

- [ ] **Step 1: Write the failing test**

Create `mobile/test/conversation_screen_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:be_my_eye/features/conversation/audio_playback.dart';
import 'package:be_my_eye/features/conversation/backend_client.dart';
import 'package:be_my_eye/features/conversation/conversation_screen.dart';
import 'package:be_my_eye/features/conversation/conversation_state.dart';
import 'package:be_my_eye/features/conversation/media_services.dart';

class _FakeBackendClient extends BackendClient {
  _FakeBackendClient() : super(baseUrl: 'http://localhost');

  @override
  Future<dynamic> sendConversation(dynamic request) async {
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

void main() {
  testWidgets('shows the idle hold-to-ask state with a matching semantics label',
      (WidgetTester tester) async {
    final state = ConversationState(
      backendClient: _FakeBackendClient(),
      mediaCaptureService: _FakeMediaCaptureService(),
      audioPlaybackService: _FakeAudioPlaybackService(),
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile && flutter test test/conversation_screen_test.dart`
Expected: FAIL — `conversation_screen.dart` does not exist yet, and `ConversationState.debugSetResponseForTest` does not exist yet.

- [ ] **Step 3: Add a test-only helper to `ConversationState`**

The second test needs a way to simulate a completed response without exercising the real backend call (the fake backend client throws `UnimplementedError`, matching what a real screen would never call directly from a widget test). Add this method to `mobile/lib/features/conversation/conversation_state.dart`, right after `playLastResponse()`:

```dart
  /// Test-only helper: sets lastResponse directly, bypassing submit(), so
  /// widget tests can verify UI reacts to a completed response without
  /// needing a real or fake network round-trip.
  @visibleForTesting
  void debugSetResponseForTest(String text) {
    _lastResponse = ConversationResponse(
      sessionId: 'test-session',
      text: text,
      audioBase64: 'test-audio',
    );
    notifyListeners();
  }
```

This requires importing `package:flutter/foundation.dart`'s `@visibleForTesting` annotation, which is already imported in this file (it's where `ChangeNotifier` comes from).

- [ ] **Step 4: Write `mobile/lib/features/conversation/conversation_screen.dart`**

```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'conversation_state.dart';

class ConversationScreen extends StatelessWidget {
  const ConversationScreen({super.key, this.sessionId = 'default-session'});

  final String sessionId;

  @override
  Widget build(BuildContext context) {
    final state = context.watch<ConversationState>();

    final String displayText;
    final String semanticsLabel;

    if (state.lastError != null) {
      displayText = state.lastError!;
      semanticsLabel = 'Error: ${state.lastError}';
    } else if (state.lastResponse != null) {
      displayText = state.lastResponse!.text;
      semanticsLabel = 'Answer: ${state.lastResponse!.text}';
    } else if (state.isBusy) {
      displayText = 'Thinking...';
      semanticsLabel = 'Thinking';
    } else {
      displayText = 'Hold to ask';
      semanticsLabel = 'Hold to ask a question';
    }

    return Scaffold(
      body: Semantics(
        label: semanticsLabel,
        liveRegion: true,
        button: true,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onLongPressStart: (_) async {
            await state.captureImage();
            await state.startAudioRecording();
          },
          onLongPressEnd: (_) async {
            await state.stopAudioRecording();
            await state.submit(sessionId: sessionId);
            await state.playLastResponse();
          },
          child: Container(
            width: double.infinity,
            height: double.infinity,
            color: Theme.of(context).colorScheme.primaryContainer,
            alignment: Alignment.center,
            padding: const EdgeInsets.all(24),
            child: Text(
              displayText,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineMedium,
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd mobile && flutter test test/conversation_screen_test.dart`
Expected: PASS — 2/2 tests.

- [ ] **Step 6: Run the full mobile test suite so far**

Run: `cd mobile && flutter test test/models_test.dart test/demo_capture_test.dart test/backend_client_test.dart test/conversation_state_test.dart test/conversation_screen_test.dart`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add mobile/lib/features/conversation/conversation_screen.dart mobile/lib/features/conversation/conversation_state.dart mobile/test/conversation_screen_test.dart
git commit -m "$(cat <<'EOF'
feat(mobile): add accessible hold-to-ask ConversationScreen

Whole-screen press-and-hold gesture, no per-feature buttons -- users
ask naturally and the backend router selects the capability. The
Semantics label always mirrors the visible state text (idle/thinking/
answer/error) so a screen reader announces the same information a
sighted user sees. Adds a @visibleForTesting debugSetResponseForTest
helper to ConversationState so the response-display path can be
verified without a real or fake network round-trip.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: `main.dart` — wire it all together, replace the stale widget test

**Files:**
- Create: `mobile/lib/main.dart`
- Modify: `mobile/test/widget_test.dart` (currently the default Flutter counter-app test — replace entirely, it doesn't match this app)

**Interfaces:**
- Consumes: `ConversationState` (Task 7), `ConversationScreen` (Task 8), `BackendClient` (Task 4), `CameraMediaCaptureService` (Task 5), `JustAudioPlaybackService` (Task 6).
- Produces: `class MyApp extends StatelessWidget` — the app entry point. Nothing later consumes this; it's the root.

**Context:** `mobile/test/widget_test.dart` currently tests a default Flutter counter app (`find.text('0')`, tapping `Icons.add`) that has nothing to do with this app — it predates any real implementation. Replace it with a test appropriate to the real `MyApp`.

- [ ] **Step 1: Write the replacement test**

Replace the full contents of `mobile/test/widget_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:be_my_eye/main.dart';

void main() {
  testWidgets('MyApp renders the hold-to-ask screen', (WidgetTester tester) async {
    await tester.pumpWidget(const MyApp());

    expect(find.text('Hold to ask'), findsOneWidget);
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mobile && flutter test test/widget_test.dart`
Expected: FAIL — `main.dart` does not exist yet.

- [ ] **Step 3: Write `mobile/lib/main.dart`**

The backend URL is injected at build/run time via `--dart-define=BACKEND_URL=...`, defaulting to the live production deployment so the app is usable out of the box during development.

```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'features/conversation/audio_playback.dart';
import 'features/conversation/backend_client.dart';
import 'features/conversation/conversation_screen.dart';
import 'features/conversation/conversation_state.dart';
import 'features/conversation/media_services.dart';

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
      ),
      child: MaterialApp(
        title: 'Be My Eye',
        theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
        home: const ConversationScreen(),
      ),
    );
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mobile && flutter test test/widget_test.dart`
Expected: PASS.

- [ ] **Step 5: Run the entire mobile test suite**

Run: `cd mobile && flutter test`
Expected: all test files pass — `models_test.dart`, `demo_capture_test.dart`, `backend_client_test.dart`, `conversation_state_test.dart`, `conversation_screen_test.dart`, `widget_test.dart`.

- [ ] **Step 6: Run static analysis across the whole app**

Run: `cd mobile && flutter analyze`
Expected: `No issues found!`

- [ ] **Step 7: Commit**

```bash
git add mobile/lib/main.dart mobile/test/widget_test.dart
git commit -m "$(cat <<'EOF'
feat(mobile): add app entry point, replace stale counter widget test

Wires the real BackendClient/CameraMediaCaptureService/
JustAudioPlaybackService into ConversationState via provider, backed
by ConversationScreen. Backend URL is injected via
--dart-define=BACKEND_URL, defaulting to the live production
deployment. Replaces the inherited default-template counter-app test
(widget_test.dart), which had nothing to do with this app, with a
test that verifies the real entry point renders the hold-to-ask
screen.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Definition of Done

- [ ] `mobile/lib/` exists and is tracked by git (verify: `git ls-files mobile/lib/`).
- [ ] `cd mobile && flutter test` passes in full — every file in `mobile/test/` (`models_test.dart`, `demo_capture_test.dart`, `backend_client_test.dart`, `conversation_state_test.dart`, `conversation_screen_test.dart`, `widget_test.dart`).
- [ ] `cd mobile && flutter analyze` reports no issues.
- [ ] No production URL, API key, or other secret is hardcoded anywhere except the `BACKEND_URL` default (a public URL, not a secret) in `main.dart`.
- [ ] Every task is committed as its own commit (or, for TDD test+implementation pairs, one atomic commit per pair — matching Plan 1's established precedent).
- [ ] Camera/microphone/audio-playback real implementations are honestly scoped: verified via `flutter analyze`, not a fake unit test claiming coverage it can't have.
