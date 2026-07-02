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
